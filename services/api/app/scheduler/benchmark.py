import asyncio
import time
from statistics import mean


WORKLOAD = [
    {"id": "invoice-1", "type": "finance", "priority": "standard", "service_ms": 120},
    {"id": "invoice-2", "type": "finance", "priority": "standard", "service_ms": 100},
    {"id": "support-urgent-1", "type": "support", "priority": "urgent", "service_ms": 30},
    {"id": "invoice-3", "type": "finance", "priority": "standard", "service_ms": 80},
    {"id": "support-urgent-2", "type": "support", "priority": "urgent", "service_ms": 40},
]


async def measure_policy(policy, workload=None):
    """Actually times a bounded single-worker workload. These are NOT inference or GPU timings."""
    items = [dict(j) for j in (workload or WORKLOAD)]
    # First job is already running when the other four arrive. Neither policy can preempt it.
    first, rest = items[0], items[1:]
    if policy == "priority":
        rest.sort(key=lambda item: 0 if item["priority"] == "urgent" else 1)
    records = []
    began = time.perf_counter()
    for item in [first] + rest:
        started = time.perf_counter()
        await asyncio.sleep(item["service_ms"] / 1000)
        ended = time.perf_counter()
        records.append({**item, "started_at_ms": round((started - began) * 1000, 2), "completed_at_ms": round((ended - began) * 1000, 2), "queue_wait_ms": round((started - began) * 1000, 2), "processing_ms": round((ended - started) * 1000, 2)})
    return {"policy": policy, "jobs": records, "mean_wait_ms": round(mean(r["queue_wait_ms"] for r in records), 2), "urgent_mean_wait_ms": round(mean(r["queue_wait_ms"] for r in records if r["priority"] == "urgent"), 2), "total_duration_ms": round((time.perf_counter() - began) * 1000, 2)}


async def compare_policies():
    fifo = await measure_policy("fifo")
    priority = await measure_policy("priority")
    delta = fifo["urgent_mean_wait_ms"] - priority["urgent_mean_wait_ms"]
    return {"kind": "measured_scheduler_microbenchmark", "label": "Measured scheduler microbenchmark · synthetic timed jobs · no inference or GPU claims", "workload": WORKLOAD, "fifo": fifo, "priority": priority, "improvement": {"urgent_wait_ms": round(delta, 2), "urgent_wait_percent": round(delta / fifo["urgent_mean_wait_ms"] * 100, 2) if fifo["urgent_mean_wait_ms"] else 0, "overall_wait_ms": round(fifo["mean_wait_ms"] - priority["mean_wait_ms"], 2)}, "method": "Same five jobs and same service durations. All are admitted at t=0; invoice-1 starts before policy selection. asyncio.sleep represents timed synthetic work. Actual wall-clock waits measured with perf_counter. Running work is not interrupted. OS scheduling adds timing jitter; this demonstrates queue policy only.", "requires_approval": True}

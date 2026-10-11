"""Deterministic agent-specific insights. No LLM claims or GPU allocation guesses."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from .models import utc_now
from .knowledge import ASSISTANT_ID


BLOCKED_TOOLS = ["network.export", "shell", "execute_code", "send_email", "make_payment", "delete_file"]


def own_workload(agent, jobs):
    own = [job for job in jobs if job["agent_id"] == agent["id"]]
    def mean_metric(key):
        values = [job.get("metrics", {}).get(key) for job in own]
        measured = [value for value in values if isinstance(value, (int, float))]
        return round(sum(measured) / len(measured), 2) if measured else None
    times = [job.get("metrics", {}).get("processing_ms") for job in own]
    measured_times = [value for value in times if isinstance(value, (int, float))]
    tokens = []
    for job in own:
        token_count = job.get("metrics", {}).get("tokens")
        if token_count is None:
            token_count = (job.get("result") or {}).get("usage", {}).get("total_tokens")
        if isinstance(token_count, int):
            tokens.append(token_count)
    timestamps = [value for job in own for value in [job.get("completed_at"), job.get("started_at"), job.get("created_at")] if value]
    last = max(timestamps) if timestamps else agent.get("created_at")
    idle_seconds = None
    if last:
        try:
            observed = datetime.fromisoformat(last)
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            idle_seconds = round(max(0, (datetime.now(timezone.utc) - observed).total_seconds()), 1)
        except ValueError:
            pass
    return {"total_jobs": len(own), "completed_jobs": sum(j["status"] == "completed" for j in own), "queued_jobs": sum(j["status"] == "queued" for j in own), "running_jobs": sum(j["status"] == "running" for j in own), "failed_jobs": sum(j["status"] in {"error", "blocked"} for j in own), "total_tokens": sum(tokens) if tokens or not own else None, "reported_token_jobs": len(tokens), "mean_queue_wait_ms": mean_metric("queue_wait_ms"), "mean_inference_latency_ms": mean_metric("inference_latency_ms"), "mean_processing_ms": mean_metric("processing_ms"), "processing_total_ms": round(sum(measured_times), 2), "measured_processing_jobs": len(measured_times), "last_activity_at": last, "idle_seconds": idle_seconds, "scope": "This agent's stored jobs only. Latency, tokens, and worker occupancy are measured request figures; no per-agent GPU use is inferred."}


def compute_cost(workload, hourly_rate):
    result = {"configured": False, "hourly_rate_usd": None, "estimated_compute_cost_usd": None, "worker_seconds": round(workload["processing_total_ms"] / 1000, 6), "scope": "Estimated compute accounting from this agent's measured worker occupancy", "note": "No hourly rate configured. Actual electricity costs, hardware allocation, payments, and money savings are not measured. Pausing an idle agent does not unload shared model weights."}
    if hourly_rate is None:
        return result
    try:
        rate = Decimal(str(hourly_rate))
        if not rate.is_finite() or rate < 0 or rate > Decimal("1000000"):
            raise ValueError("Rate must be finite, non-negative, and at most one million USD/hour.")
        cost = Decimal(str(workload["processing_total_ms"])) / Decimal("3600000") * rate
        result.update(configured=True, hourly_rate_usd=str(rate), estimated_compute_cost_usd=str(cost.quantize(Decimal("0.000001"))), note="User-configured hourly rate × measured job processing seconds / 3600. This is a bookkeeping estimate, not an actual charge, electricity reading, GPU allocation, or payment action. Processing time includes tool work and inference waits.")
    except (InvalidOperation, ValueError):
        result["note"] = "Configured hourly rate is invalid; no compute cost was estimated. Use a finite, non-negative USD/hour rate."
    return result


def recommendations_for(agent, workload, agents, jobs, policy):
    suggestions = []
    def add(key, title, explanation, evidence, action="review_jobs", approval=False):
        target_id = "optimizer" if action == "open_optimizer" else agent["id"]
        suggestions.append({"id": agent["id"] + ":" + key, "title": title, "explanation": explanation, "evidence": evidence, "action": {"type": action, "agent_id": target_id}, "requires_approval": approval})
    controllable = agent["role"] in {"hr", "finance", "support", "custom"}
    if not agent.get("enabled", True) and controllable:
        add("resume", "Resume this agent when needed", "Existing queued work is retained. Resuming permits this agent to receive and execute new work; it does not download or load model weights by itself.", {"queued_jobs": workload["queued_jobs"]}, "resume_agent", True)
    peers = [other for other in agents if other["id"] != agent["id"] and other["role"] == agent["role"] and set(other.get("source_ids", [])) == set(agent.get("source_ids", []))]
    if peers and controllable:
        add("overlap", "Review overlapping agent templates", "Other agents use this same role and local source. Check whether their purposes overlap before deciding which agents should accept new work.", {"same_role_source_agent_ids": [other["id"] for other in peers], "this_agent_jobs": workload["total_jobs"]}, "review_agents")
    if controllable and agent.get("enabled", True) and not workload["running_jobs"] and not workload["queued_jobs"] and (not workload["total_jobs"] or (workload["idle_seconds"] or 0) >= 300):
        add("pause", "Pause unused work intake", "This agent has no active or queued work. Pausing prevents new submissions while keeping its history. It does not reclaim a private GPU partition or unload the shared Nemotron model.", {"total_jobs": workload["total_jobs"], "last_activity_at": workload["last_activity_at"], "idle_seconds": workload["idle_seconds"]}, "pause_agent", True)
    if workload["failed_jobs"]:
        add("errors", "Inspect failed requests first", "Review this agent's own errors and source availability before submitting a larger batch.", {"failed_jobs": workload["failed_jobs"]})
    if (workload["mean_inference_latency_ms"] or 0) > 10000:
        add("latency", "Review long inference requests", "This agent's measured inference latency is high. Compare shorter, well-scoped requests before changing generation limits; no throughput improvement is assumed.", {"mean_inference_latency_ms": workload["mean_inference_latency_ms"], "reported_token_jobs": workload["reported_token_jobs"]}, "open_optimizer")
    urgent = [j for j in jobs if j["agent_id"] == agent["id"] and j["status"] == "queued" and j["priority"] == "urgent"]
    if urgent and policy == "fifo":
        add("urgent", "Measure priority scheduling for urgent work", "This agent has urgent queued requests under FIFO. Run the measured comparison before approving priority scheduling; running tasks must finish safely.", {"urgent_queued_jobs": len(urgent), "scheduler_policy": policy}, "open_optimizer")
    if not suggestions:
        add("observe", "Keep collecting measured evidence", "There is no observed issue requiring an automatic change. Use this agent's own task history and source evidence to decide the next request.", {"completed_jobs": workload["completed_jobs"], "mean_processing_ms": workload["mean_processing_ms"]})
    return suggestions


def invoice_evidence(agent, jobs, settings):
    completed = [job for job in jobs if job["agent_id"] == agent["id"] and job["status"] == "completed" and job.get("source_ids") and (job.get("result") or {}).get("synthetic") is False and (job.get("result") or {}).get("calculations")]
    if completed:
        job = max(completed, key=lambda item: item["completed_at"] or item["created_at"])
        result = job["result"]
        return {"available": True, "origin": "Stored completed Finance job", "source_job_id": job["id"], **{key: result.get(key) for key in ["calculations", "duplicate_invoices", "overdue_rows", "rows", "sources"]}}
    return {"available": False, "error": "No completed invoice review from your attached CSV knowledge is available. Attach an invoice CSV and run a Finance task to calculate actual balances.", "source_job_id": None}


def source_details(agent, knowledge):
    if knowledge is None:
        return []
    allowed = set(knowledge.accessible_ids(agent))
    return [{**source, "available": bool(source["text_length"] and (source["status"] == "ready" or source.get("last_synced_at"))), "synthetic": False} for source in knowledge.list() if source["id"] in allowed]


def build_insights(agent, store, settings, knowledge=None):
    agents, jobs = [a for a in store.active("agents") if a["id"] != ASSISTANT_ID], store.all("jobs")
    own = [job for job in jobs if job["agent_id"] == agent["id"]]
    workload = own_workload(agent, jobs)
    policy = store.get("settings", "scheduler")["policy"]
    queued = [job for job in jobs if job["status"] == "queued" and next((a.get("enabled", True) for a in agents if a["id"] == job["agent_id"]), False)]
    queued.sort(key=lambda j: ((0 if j["priority"] == "urgent" else 1) if policy == "priority" else 0, j["created_at"]))
    positions = [{"job_id": job["id"], "position": index + 1, "priority": job["priority"]} for index, job in enumerate(queued) if job["agent_id"] == agent["id"]]
    cost = compute_cost(workload, settings.hourly_rate_usd)
    suggestions = recommendations_for(agent, workload, agents, jobs, policy)
    latest = max(own, key=lambda job: job["created_at"]) if own else None
    sources = source_details(agent, knowledge)
    role_details = {"kind": "knowledge", "document": agent.get("source", ""), "retrieval": "local SQLite FTS5", "latest_sources": (latest.get("result") or {}).get("sources", []) if latest else []}
    if agent["role"] == "support":
        role_details.update(kind="support_rag", knowledge_sources=[source["id"] for source in sources], draft_only=True)
    elif agent["role"] in {"finance", "optimizer"}:
        allocation = [{"agent": {"id": a["id"], "name": a["name"], "role": a["role"], "status": a["status"], "enabled": a.get("enabled", True)}, "workload": own_workload(a, jobs), "cost": compute_cost(own_workload(a, jobs), settings.hourly_rate_usd), "recommendations": recommendations_for(a, own_workload(a, jobs), agents, jobs, policy)} for a in agents]
        if agent["role"] == "finance":
            evidence = invoice_evidence(agent, jobs, settings)
            role_details = {"kind": "invoice_review", "invoice_evidence": evidence, "allocation_review": {"agents": allocation, "optimizer_agent_id": "optimizer", "note": "Business invoice balances are separate from optional compute accounting. No payment, GPU partition, or cost saving is inferred."}}
            if evidence.get("available") and evidence.get("duplicate_invoices"):
                suggestions.insert(0, {"id": agent["id"] + ":allocation", "title": "Reconcile duplicate invoices before allocation review", "explanation": "Inspect the exact duplicate source rows and unpaid balances, then review each agent's measured usage in Optimizer. Business invoices are not compute charges.", "evidence": {"source_job_id": evidence.get("source_job_id"), "duplicate_invoice_ids": [item["invoice_id"] for item in evidence["duplicate_invoices"]], "outstanding_total": evidence["calculations"]["outstanding_total"], "deduplicated_outstanding_total": evidence["calculations"]["deduplicated_outstanding_total"]}, "action": {"type": "open_optimizer", "agent_id": "optimizer"}, "requires_approval": False})
        else:
            finance = next((a for a in agents if a["id"] == "finance"), None)
            comparison = store.get("settings", "last_comparison")
            role_details = {"kind": "allocation_review", "agents": allocation, "latest_comparison": comparison["result"] if comparison else None, "finance_evidence": invoice_evidence(finance, jobs, settings) if finance else None, "note": "Suggestions are deterministic observations from each agent's own stored jobs. Idle pause controls stop work intake, not shared model memory. Only measured scheduler scenarios support scheduling claims."}
    elif agent["role"] == "security":
        blocked = [event for event in store.all("events") if event["type"] == "security_blocked"]
        role_details = {"kind": "security", "enforcement_features": [{"name": "Role and agent tool allowlists", "enforced": True, "detail": "Every workflow is checked before its audited tool runs."}, {"name": "Explicit knowledge access", "enforced": True, "detail": "Business agents read only shared or assigned library IDs. Source text and custom purposes cannot grant tools, paths, or code execution."}, {"name": "Loopback inference and browser boundary", "enforced": True, "detail": "Remote browser origins, non-loopback Host headers, hosted model URLs, inference redirects, and environment proxy forwarding are refused."}, {"name": "Public source fetch restrictions", "enforced": True, "detail": "Website and API integrations make bounded read-only GET requests to validated public IPs. Private network addresses, URL credentials, and unsafe redirects are blocked."}, {"name": "Grounded model evidence", "enforced": True, "detail": "Citation IDs and Finance exact fact fields are validated. Documents cannot grant new tools."}, {"name": "Human approval for queue policy", "enforced": True, "detail": "Policy changes require an explicit approved request. Running work is not preempted."}], "blocked_events": blocked[-50:], "network_export_implemented": False, "external_payment_implemented": False}
    return {"agent": agent, "generated_at": utc_now(), "workload": workload, "queue": {"policy": policy, "positions": positions, "paused_jobs_count": workload["queued_jobs"] if not agent.get("enabled", True) else 0}, "sources": sources, "permissions": {"allowed_tools": agent["tools"], "blocked_tools": BLOCKED_TOOLS, "enforced": True, "external_actions": False}, "recommendations": suggestions, "cost": cost, "role_details": role_details}

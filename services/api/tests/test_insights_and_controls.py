import asyncio
import time
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest
from app.agents import DEFAULT_AGENTS
from app.config import Settings
from app.insights import build_insights, compute_cost, own_workload
from app.main import create_app
from app.models import AgentCreate
from app.scheduler import select_next
from app.security import validate_configuration
from app.storage import Store
from app.tools.hr import retrieve_policy
from app.tools.workflows import WorkflowEvidenceError, run_workflow


class SlowGroundedLLM:
    async def health_check(self, force=False):
        return {"available": True, "model": "test-double"}
    async def chat(self, system, prompt, max_tokens=None):
        await asyncio.sleep(0.18)
        return {"answer": "Use the Forgot password link; never share passwords [1]." if "support playbook" in system else "Full-time employees receive twenty days of PTO [1].", "usage": {"total_tokens": 10}, "inference_latency_ms": 180}


def wait_for(client, job_id, states):
    for _ in range(200):
        job = client.get("/api/jobs/" + job_id).json()
        if job["status"] in states:
            return job
        time.sleep(0.01)
    raise AssertionError("Job did not reach expected state")


def test_pause_running_work_finishes_holds_queue_and_resume_releases(tmp_path):
    app = create_app(Settings(db_path=tmp_path / "state.db"), SlowGroundedLLM())
    with TestClient(app, base_url="http://localhost") as client:
        first = client.post("/api/jobs", json={"agent_id": "hr", "prompt": "How many days of PTO?"}).json()
        wait_for(client, first["id"], {"running"})
        second = client.post("/api/jobs", json={"agent_id": "hr", "prompt": "How many PTO days?"}).json()
        paused = client.post("/api/agents/hr/control", json={"action": "pause"}).json()
        assert paused["agent"]["enabled"] is False and paused["pause_pending"] is True
        assert paused["running_jobs_interrupted"] is False
        assert client.post("/api/jobs", json={"agent_id": "hr", "prompt": "Read policy"}).status_code == 409
        assert wait_for(client, first["id"], {"completed", "error"})["status"] == "completed"
        time.sleep(0.05)
        assert client.get("/api/jobs/" + second["id"]).json()["status"] == "queued"
        held = client.get("/api/agents/hr/insights").json()
        assert held["agent"]["status"] == "paused"
        assert held["queue"]["paused_jobs_count"] == 1 and held["queue"]["positions"] == []
        support = client.post("/api/jobs", json={"agent_id": "support", "prompt": "Customer cannot access the account portal"}).json()
        assert wait_for(client, support["id"], {"completed", "error"})["status"] == "completed"
        resumed = client.post("/api/agents/hr/control", json={"action": "resume"}).json()
        assert resumed["agent"]["enabled"] is True
        assert wait_for(client, second["id"], {"completed", "error"})["status"] == "completed"
        own = client.get("/api/agents/hr/insights").json()
        assert own["workload"]["total_jobs"] == 2
        assert own["workload"]["total_tokens"] == 20
        assert own["cost"]["configured"] is False
        assert own["cost"]["estimated_compute_cost_usd"] is None


def test_pause_is_durable_and_protected_stations_cannot_pause(tmp_path):
    path = tmp_path / "state.db"
    with TestClient(create_app(Settings(db_path=path), SlowGroundedLLM()), base_url="http://localhost") as client:
        assert client.post("/api/agents/hr/control", json={"action": "pause"}).status_code == 200
        assert client.post("/api/agents/security/control", json={"action": "pause"}).status_code == 409
        assert client.post("/api/agents/optimizer/control", json={"action": "pause"}).status_code == 409
        assert client.post("/api/agents/hr/control", json={"action": "delete"}).status_code == 422
    with TestClient(create_app(Settings(db_path=path), SlowGroundedLLM()), base_url="http://localhost") as restarted:
        hr = next(agent for agent in restarted.get("/api/agents").json() if agent["id"] == "hr")
        assert hr["enabled"] is False and hr["status"] == "paused"
        assert restarted.post("/api/jobs", json={"agent_id": "hr", "prompt": "Read PTO policy"}).status_code == 409


def test_scheduler_excludes_paused_urgent_agent():
    jobs = [{"id": "held", "agent_id": "hr", "status": "queued", "priority": "urgent", "created_at": "1"}, {"id": "eligible", "agent_id": "support", "status": "queued", "priority": "standard", "created_at": "2"}]
    agents = [{"id": "hr", "enabled": False}, {"id": "support", "enabled": True}]
    assert select_next(jobs, "priority", agents)["id"] == "eligible"


def test_insights_statistics_are_owned_and_cost_is_explicit_estimate(tmp_path):
    store = Store(tmp_path / "state.db")
    hr = store.get("agents", "hr")
    store.put("jobs", {"id": "hr1", "agent_id": "hr", "status": "completed", "created_at": "2026-10-10T10:00:00+00:00", "completed_at": "2026-10-10T11:00:00+00:00", "metrics": {"processing_ms": 3600000, "inference_latency_ms": 18000, "queue_wait_ms": 4, "tokens": 20}, "result": {"sources": []}})
    store.put("jobs", {"id": "other", "agent_id": "finance", "status": "completed", "created_at": "2026-10-10T10:00:00+00:00", "completed_at": "2026-10-10T11:00:00+00:00", "metrics": {"processing_ms": 7200000, "tokens": 90000}})
    insight = build_insights(hr, store, Settings(db_path=tmp_path / "state.db", hourly_rate_usd="2.50"))
    assert insight["workload"]["total_jobs"] == 1
    assert insight["workload"]["total_tokens"] == 20
    assert insight["workload"]["processing_total_ms"] == 3600000
    latency_review = next(rec for rec in insight["recommendations"] if rec["action"]["type"] == "open_optimizer")
    assert latency_review["evidence"]["mean_inference_latency_ms"] == 18000
    assert latency_review["action"]["agent_id"] == "optimizer"
    assert Decimal(insight["cost"]["estimated_compute_cost_usd"]) == Decimal("2.50")
    assert "estimate" in insight["cost"]["note"]
    for unsafe in ["NaN", "-1", "Infinity", "not-money"]:
        assert compute_cost(insight["workload"], unsafe)["configured"] is False
    guardian = build_insights(store.get("agents", "security"), store, Settings())
    assert not any(rec["action"]["type"] == "pause_agent" for rec in guardian["recommendations"])
    finance = build_insights(store.get("agents", "finance"), store, Settings())
    evidence = finance["role_details"]["invoice_evidence"]
    assert evidence["calculations"]["outstanding_total"] == "6200.50"
    assert evidence["duplicate_invoices"][0]["invoice_id"] == "INV-1001"
    assert finance["recommendations"][0]["action"] == {"type": "open_optimizer", "agent_id": "optimizer"}
    store.close()


async def test_support_retrieval_citations_legacy_source_and_missing_document(tmp_path):
    settings = Settings()
    sources = retrieve_policy(settings.data_dir / "support_playbook.txt", "Customer cannot access account; password reset")
    assert sources[0]["document"] == "support_playbook.txt"
    assert sources[0]["page"] == 1
    assert "Never ask for a password" in sources[0]["snippet"]
    legacy = {**DEFAULT_AGENTS[2], "source": "support_tickets.json"}
    result = await run_workflow(legacy, {"prompt": "Customer cannot access the account portal"}, settings, SlowGroundedLLM())
    assert result["retrieval"] == "local SQLite FTS5" and result["draft_only"] is True
    assert result["sources"][0]["document"] == "support_playbook.txt"
    assert result["context_sources"][0]["document"] == "support_tickets.json"
    validate_configuration(AgentCreate(name="Support", role="support", purpose="Draft grounded support replies", tools=["draft_support_reply"], source="support_playbook.txt"))
    (tmp_path / "support_tickets.json").write_text("[]")
    with pytest.raises(WorkflowEvidenceError) as captured:
        await run_workflow(legacy, {"prompt": "Read refund policy"}, Settings(data_dir=tmp_path), SlowGroundedLLM())
    assert captured.value.result["missing_source"] == "support_playbook.txt"


async def test_support_omitted_citations_get_only_real_retriever_references():
    class UncitedLLM:
        async def chat(self, system, prompt, max_tokens=None):
            return {"answer": "Use the Forgot password link and do not share passwords."}
    result = await run_workflow(DEFAULT_AGENTS[2], {"prompt": "Draft a helpful response to a fictional customer who cannot access their account."}, Settings(), UncitedLLM())
    assert result["sources"][0]["page"] == 1
    assert result["citation_origin"] == "retriever"
    assert "[1] support_playbook.txt · page 1" in result["answer"]
    assert "Retrieved knowledge references" in result["answer"]


def test_security_insights_show_actual_block_log(tmp_path):
    with TestClient(create_app(Settings(db_path=tmp_path / "state.db"), SlowGroundedLLM()), base_url="http://localhost") as client:
        assert client.get("/api/agents/not-real/insights").status_code == 404
        blocked = client.post("/api/security/demo", json={"agent_id": "finance"}).json()
        insight = client.get("/api/agents/security/insights").json()
        assert insight["role_details"]["blocked_events"][-1]["id"] == blocked["event"]["id"]
        assert insight["role_details"]["external_payment_implemented"] is False
        assert all(feature["enforced"] for feature in insight["role_details"]["enforcement_features"])

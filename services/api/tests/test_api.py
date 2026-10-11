import asyncio
import time
import json
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.tools.finance import analyze_invoices
from conftest import FIXTURES, attach_fixtures


class TestLLM:
    """Explicit test double only. The production app has no fixture inference path."""
    async def health_check(self, force=False):
        return {"available": True, "model": "test-double", "base_url": "http://localhost/test", "local_only": True, "error": None}

    async def chat(self, system, prompt, max_tokens=None):
        await asyncio.sleep(0.03)
        answer = "The fictional ledger contains duplicate INV-1001. Raw overdue total is $4,950.50; deduplicated overdue total is $3,750.50." if "Deterministic evidence:" in prompt else "The fictional handbook grants 20 days of PTO [1]."
        return {"answer": answer, "model": "test-double", "inference_latency_ms": 30, "usage": {"total_tokens": 20}, "source": "test_double"}

    async def structured_output(self, system, prompt):
        result = await self.chat(system, prompt)
        evidence = json.loads(prompt.split("Exact audited evidence: ")[1].split("\nReturn this JSON schema:")[0])
        result["structured"] = {"summary": "Review duplicate records before acting. Prioritize overdue unpaid invoices for review.", "duplicate_invoice_ids": evidence["duplicate_invoice_ids"], "overdue_total": evidence["calculations"]["overdue_total"], "deduplicated_overdue_total": evidence["calculations"]["deduplicated_overdue_total"]}
        return result


@pytest.fixture
def client(tmp_path):
    settings = Settings(db_path=tmp_path / "test.db", upload_dir=tmp_path / "uploads")
    with TestClient(create_app(settings, TestLLM()), base_url="http://localhost") as client:
        attach_fixtures(client)
        yield client


def wait_job(client, job_id):
    for _ in range(150):
        job = client.get("/api/jobs/" + job_id).json()
        if job["status"] in {"completed", "error", "blocked"}:
            return job
        time.sleep(0.01)
    raise AssertionError("worker did not finish")


def test_full_hr_job_state_provenance_and_metrics(client):
    assert client.get("/api/health").json()["status"] == "ok"
    response = client.post("/api/jobs", json={"agent_id": "hr", "prompt": "How many days of PTO do employees receive?"})
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    job = wait_job(client, response.json()["id"])
    assert job["status"] == "completed"
    assert "20 days" in job["result"]["answer"]
    assert job["result"]["sources"][0]["page"] == 1
    assert job["started_at"] and job["completed_at"]
    assert job["metrics"]["tokens"] == 20
    assert client.get("/api/metrics").json()["completed_jobs"] == 1


def test_finance_returns_inspectable_deterministic_results(client):
    response = client.post("/api/jobs", json={"agent_id": "finance", "prompt": "Find duplicate and overdue invoices"})
    job = wait_job(client, response.json()["id"])
    assert job["status"] == "completed"
    assert job["result"]["calculations"]["overdue_total"] == analyze_invoices(FIXTURES / "invoices.csv", date.today())["calculations"]["overdue_total"]
    assert len(job["result"]["rows"]) == 8


def test_agent_studio_creation_and_privilege_refusal(client):
    source_id = client.get("/api/sources").json()[0]["id"]
    config = {"name": "Demo HR", "role": "hr", "purpose": "Answer attached handbook questions", "tools": ["read_policy"], "source_ids": [source_id]}
    assert client.post("/api/agents", json=config).status_code == 201
    config["tools"] = ["analyze_invoices"]
    assert client.post("/api/agents", json=config).status_code == 403
    config["tools"] = ["shell"]
    assert client.post("/api/agents", json=config).status_code == 422


def test_policy_requires_explicit_approval_and_security_never_executes(client):
    assert client.post("/api/optimizer/approve", json={"policy": "priority", "approved": False}).status_code == 403
    response = client.post("/api/optimizer/approve", json={"policy": "priority", "approved": True})
    assert response.json()["running_jobs_interrupted"] is False
    assert client.get("/api/health").json()["scheduler_policy"] == "priority"
    block = client.post("/api/security/demo").json()
    assert block["blocked"] and not block["executed"]
    assert not block["network_request_made"] and not block["files_modified"]
    assert "network.export" in block["reason"]


def test_external_browser_origins_and_rebinding_hosts_refused(client):
    assert client.post("/api/security/demo", headers={"Origin": "https://attacker.invalid"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "attacker.invalid"}).status_code == 403
    assert client.get("/api/health", headers={"Origin": "http://localhost:5173"}).status_code == 200


def test_missing_agent_and_unknown_fields_are_clear_errors(client):
    assert client.post("/api/jobs", json={"agent_id": "missing", "prompt": "Read policy"}).status_code == 404
    assert client.post("/api/jobs", json={"agent_id": "hr", "prompt": "Read policy", "command": "export"}).status_code == 422

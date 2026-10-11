from fastapi.testclient import TestClient
import pytest
from app.config import Settings
from app.main import create_app
from app.storage import Store
from test_knowledge import GroundedLLM
from test_delete import deletion_client


def agent_config(**updates):
    return {"name": "Legal guide", "role": "custom", "purpose": "Explain our legal documents using attached source evidence.", "tools": ["read_knowledge"], **updates}


def test_durable_category_and_agent_selection_survive_restart(tmp_path):
    settings = Settings(db_path=tmp_path / "state.db", upload_dir=tmp_path / "uploads")
    with TestClient(create_app(settings, GroundedLLM()), base_url="http://localhost") as client:
        defaults = client.get("/api/categories").json()
        assert [category["id"] for category in defaults] == ["hr", "finance", "support", "security", "optimizer", "custom"]
        response = client.post("/api/categories", json={"name": "  Legal   & compliance  ", "color": "#AABBCC"})
        assert response.status_code == 201, response.text
        category = response.json()
        assert category["name"] == "Legal & compliance" and category["color"] == "#aabbcc" and category["built_in"] is False
        created = client.post("/api/agents", json=agent_config(category_id=category["id"]))
        assert created.status_code == 201
        agent = created.json()
        assert agent["category_id"] == category["id"]
        assert agent["role"] == "custom" and agent["tools"] == ["read_knowledge"]
    with TestClient(create_app(settings, GroundedLLM()), base_url="http://localhost") as restarted:
        assert restarted.get("/api/categories").json()[-1] == category
        assert next(item for item in restarted.get("/api/agents").json() if item["id"] == agent["id"])["category_id"] == category["id"]


def test_category_migration_preserves_ids_existing_choices_and_history(tmp_path):
    settings = Settings(db_path=tmp_path / "state.db", upload_dir=tmp_path / "uploads")
    store = Store(settings.db_path)
    custom = {"id": "existing-legal", "name": "Legal", "color": "#cc8844", "built_in": False}
    store.put("categories", custom)
    hr = store.get("agents", "hr")
    hr.update(name="Avery", purpose="Answer our own policies plainly.", category_id=custom["id"])
    store.put("agents", hr)
    finance = store.get("agents", "finance")
    finance.update(name="Ledger", deleted_at="2026-10-11T10:00:00+00:00")
    store.put("agents", finance)
    history = {"id": "historical", "agent_id": "hr", "status": "completed", "created_at": "2026-10-10", "result": {"answer": "Recorded history"}, "metrics": {}}
    store.put("jobs", history)
    store.close()
    with TestClient(create_app(settings, GroundedLLM()), base_url="http://localhost") as client:
        restored_hr = next(agent for agent in client.get("/api/agents").json() if agent["id"] == "hr")
        assert restored_hr["name"] == "Avery" and restored_hr["purpose"] == hr["purpose"] and restored_hr["category_id"] == custom["id"]
        deleted = client.get("/api/agents/deleted").json()[0]
        assert deleted["id"] == "finance" and deleted["name"] == "Ledger" and deleted["category_id"] == "finance"
        assert client.get("/api/jobs/historical").json() == history
        defaults = client.get("/api/agents").json()
        assert all(agent.get("category_id") for agent in defaults)


def test_categories_never_grant_role_or_tool_permissions(deletion_client):
    client, app, settings = deletion_client
    category = client.post("/api/categories", json={"name": "Review team", "color": "#5588bb"}).json()
    assert client.post("/api/agents", json=agent_config(category_id="security", tools=["inspect_permissions"])).status_code == 403
    assert client.post("/api/agents", json=agent_config(category_id=category["id"], tools=["shell"])).status_code == 422
    created = client.post("/api/agents", json=agent_config(category_id="optimizer")).json()
    assert created["role"] == "custom" and created["tools"] == ["read_knowledge"]
    assert client.post("/api/agents/" + created["id"] + "/allocation-review").status_code == 403
    finance = client.post("/api/agents", json=agent_config(role="finance", tools=["analyze_invoices"], category_id=category["id"])).json()
    assert finance["role"] == "finance" and finance["category_id"] == category["id"]
    assert client.post("/api/agents", json=agent_config(category_id="missing")).status_code == 422
    fallback = client.post("/api/agents", json=agent_config()).json()
    assert fallback["category_id"] == "custom"


@pytest.mark.parametrize("payload", [{"name": " ", "color": "#123456"}, {"name": "Team", "color": "red"}, {"name": "Team", "color": "#fff"}, {"name": "Team", "color": "#123456", "tools": ["shell"]}])
def test_category_validation_blocks_malformed_style_and_permissions(deletion_client, payload):
    client, app, settings = deletion_client
    assert client.post("/api/categories", json=payload).status_code == 422
    assert len(client.get("/api/categories").json()) == 6


def test_category_duplicate_names_are_normalized(deletion_client):
    client, app, settings = deletion_client
    assert client.post("/api/categories", json={"name": " FINANCE ", "color": "#123456"}).status_code == 409
    assert client.post("/api/categories", json={"name": "Legal team", "color": "#123456"}).status_code == 201
    assert client.post("/api/categories", json={"name": "legal   TEAM", "color": "#654321"}).status_code == 409


def test_existing_agent_category_change_preserves_identity_permissions_and_history(deletion_client):
    client, app, settings = deletion_client
    category = client.post("/api/categories", json={"name": "Compliance", "color": "#123456"}).json()
    before = app.state.store.get("agents", "hr")
    history = {"id": "old-policy", "agent_id": "hr", "status": "completed", "created_at": "2026-10-11", "result": {"answer": "Recorded history"}, "metrics": {}}
    app.state.store.put("jobs", history)
    response = client.post("/api/agents/hr/category", json={"category_id": category["id"]})
    assert response.status_code == 200
    after = response.json()
    assert after["category_id"] == category["id"]
    assert {key: value for key, value in after.items() if key != "category_id"} == {key: value for key, value in before.items() if key != "category_id"}
    assert client.get("/api/jobs/old-policy").json() == history
    changed = client.get("/api/activity").json()[-1]
    assert changed["type"] == "category_changed" and changed["agent_id"] == "hr"
    assert changed["detail"]["previous_category_id"] == "hr"
    assert client.post("/api/agents/hr/category", json={"category_id": "security", "tools": ["inspect_permissions"]}).status_code == 422
    assert client.post("/api/agents/hr/category", json={"category_id": "missing"}).status_code == 422
    client.post("/api/agents/hr/delete")
    assert client.post("/api/agents/hr/category", json={"category_id": category["id"]}).status_code == 404


def test_allocation_review_is_actual_saved_evidence_and_durable_interaction(deletion_client):
    client, app, settings = deletion_client
    # Recorded completed job evidence, not a fixture inference or invented audit.
    source = {"id": "uploaded-csv", "name": "Ledger.csv", "kind": "file", "status": "ready", "text": "vendor,invoice_id,due_date,amount,status,category", "shared": False}
    app.state.store.put("sources", source)
    facts = {"as_of": "2026-10-11", "outstanding_total": "125.00", "overdue_total": "125.00", "deduplicated_outstanding_total": "125.00", "deduplicated_overdue_total": "125.00", "method": "Recorded Decimal calculations"}
    job = {"id": "finance-audit", "agent_id": "finance", "status": "completed", "priority": "standard", "created_at": "2026-10-11T00:00:00+00:00", "completed_at": "2026-10-11T00:00:01+00:00", "source_ids": [source["id"]], "result": {"synthetic": False, "calculations": facts, "duplicate_invoices": [], "rows": [], "overdue_rows": [], "sources": [{"source_id": source["id"], "document": "Ledger.csv"}]}, "metrics": {"processing_ms": 1000, "tokens": 12}}
    app.state.store.put("jobs", job)
    policy = client.get("/api/health").json()["scheduler_policy"]
    response = client.post("/api/agents/optimizer/allocation-review", json={"finance_agent_id": "finance"})
    assert response.status_code == 200, response.text
    review, interaction = response.json()["review"], response.json()["interaction"]
    assert review["finance_evidence"]["source_job_id"] == job["id"]
    assert review["finance_evidence"]["calculations"]["outstanding_total"] == "125.00"
    assert review["finance_workload"]["total_tokens"] == 12
    assert review["finance_workload"]["processing_total_ms"] == 1000
    assert interaction["status"] == "completed" and interaction["kind"] == "allocation_review"
    assert interaction["from_agent_id"] == "optimizer" and interaction["to_agent_id"] == "finance"
    assert interaction["started_at"] <= interaction["completed_at"]
    event = next(event for event in client.get("/api/activity").json() if event["id"] == interaction["event_id"])
    assert event["type"] == "agent_interaction" and event["detail"]["interaction_id"] == interaction["id"]
    assert event["detail"]["evidence_source_job_id"] == job["id"]
    assert client.get("/api/health").json()["scheduler_policy"] == policy
    assert app.state.store.get("jobs", job["id"]) == job
    assert app.state.llm.calls == []


def test_allocation_review_without_invoice_evidence_is_honest_and_role_gated(deletion_client):
    client, app, settings = deletion_client
    response = client.post("/api/agents/optimizer/allocation-review")
    assert response.status_code == 200
    review = response.json()["review"]
    assert review["finance_evidence"]["available"] is False
    assert review["finance_workload"]["total_jobs"] == 0
    assert review["findings"][-1]["kind"] == "invoice_evidence_unavailable"
    count = len([event for event in client.get("/api/activity").json() if event["type"] == "agent_interaction"])
    assert client.post("/api/agents/hr/allocation-review").status_code == 403
    assert client.post("/api/agents/optimizer/allocation-review", json={"finance_agent_id": "hr"}).status_code == 422
    client.post("/api/agents/finance/delete")
    assert client.post("/api/agents/optimizer/allocation-review").status_code == 409
    assert client.post("/api/agents/optimizer/allocation-review", json={"finance_agent_id": "finance"}).status_code == 404
    assert len([event for event in client.get("/api/activity").json() if event["type"] == "agent_interaction"]) == count
    client.post("/api/agents/optimizer/delete")
    assert client.post("/api/agents/optimizer/allocation-review").status_code == 404

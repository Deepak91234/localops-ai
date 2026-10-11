import asyncio
from pathlib import Path
import time
from fastapi.testclient import TestClient
import pytest
from app.config import Settings
from app.events import EventBus
from app.knowledge import ASSISTANT_ID, KnowledgeError, KnowledgeLibrary
from app.main import create_app
from app.models import Job, SourceLink, utc_now
from app.scheduler import select_next
from app.storage import Store
from conftest import attach
from test_api import wait_job
from test_knowledge import GroundedLLM, submit


@pytest.fixture
def deletion_client(tmp_path):
    settings = Settings(db_path=tmp_path / "state.db", upload_dir=tmp_path / "uploads")
    app = create_app(settings, GroundedLLM())
    with TestClient(app, base_url="http://localhost") as client:
        yield client, app, settings


def queued_job(agent, source_ids=None):
    return Job(id="pending-" + agent, agent_id=agent, type="custom", prompt="Explain the Aurora checkpoint", priority="standard", status="queued", created_at=utc_now(), source_ids=source_ids or []).model_dump(mode="json")


def test_agent_delete_cancel_restore_history_and_no_default_reseed(tmp_path):
    settings = Settings(db_path=tmp_path / "state.db", upload_dir=tmp_path / "uploads")
    with TestClient(create_app(settings, GroundedLLM()), base_url="http://localhost") as client:
        attach(client, "aurora.txt", "Aurora checkpoint is Thursday.", ["hr"])
        completed = submit(client, "hr", "When is the Aurora checkpoint?")
        client.post("/api/agents/hr/control", json={"action": "pause"})
        store = client.app.state.store
        queued = queued_job("hr")
        store.put("jobs", queued)
        response = client.post("/api/agents/hr/delete")
        assert response.status_code == 200, response.text
        assert response.json()["cancelled_jobs"] == [queued["id"]]
        assert "hr" not in {agent["id"] for agent in client.get("/api/agents").json()}
        assert client.get("/api/agents/deleted").json()[0]["id"] == "hr"
        assert client.get("/api/jobs/" + completed["id"]).json() == completed
        cancelled = client.get("/api/jobs/" + queued["id"]).json()
        assert cancelled["status"] == "error" and cancelled["metrics"]["cancelled_by_agent_deletion"]
        assert client.post("/api/jobs", json={"agent_id": "hr", "prompt": "Read Aurora"}).status_code == 404
        assert client.get("/api/agents/hr/insights").status_code == 404
        assert client.post("/api/agents/hr/control", json={"action": "resume"}).status_code == 404
        assert client.post("/api/agents/hr/sources", json={"source_ids": []}).status_code == 404
        assert "hr" not in {agent["id"] for agent in client.get("/api/metrics").json()["agents"]}
        assert "hr" not in {item["agent"]["id"] for item in client.get("/api/agents/optimizer/insights").json()["role_details"]["agents"]}
    with TestClient(create_app(settings, GroundedLLM()), base_url="http://localhost") as restarted:
        assert "hr" not in {agent["id"] for agent in restarted.get("/api/agents").json()}
        restored = restarted.post("/api/agents/hr/restore").json()
        assert restored["deleted_at"] is None and restored["enabled"] is False
        assert restarted.get("/api/jobs/" + queued["id"]).json()["status"] == "error"
        restarted.post("/api/agents/hr/control", json={"action": "resume"})
        assert submit(restarted, "hr", "When is the Aurora checkpoint?")["status"] == "completed"
        assert restarted.get("/api/jobs/" + queued["id"]).json()["status"] == "error"


def test_running_agent_and_source_deletion_are_refused(tmp_path):
    class SlowLLM(GroundedLLM):
        async def chat(self, *args, **kwargs):
            await asyncio.sleep(0.25)
            return await super().chat(*args, **kwargs)
    app = create_app(Settings(db_path=tmp_path / "state.db", upload_dir=tmp_path / "uploads"), SlowLLM())
    with TestClient(app, base_url="http://localhost") as client:
        source = attach(client, "aurora.txt", "Aurora checkpoint is Thursday.", ["hr"])
        submitted = client.post("/api/jobs", json={"agent_id": "hr", "prompt": "Explain Aurora"}).json()
        for _ in range(100):
            if client.get("/api/jobs/" + submitted["id"]).json()["status"] == "running":
                break
            time.sleep(0.005)
        else:
            raise AssertionError("Job did not start")
        assert client.post("/api/agents/hr/delete").status_code == 409
        assert client.post("/api/sources/" + source["id"] + "/delete").status_code == 409
        assert not app.state.store.get("agents", "hr").get("deleted_at")
        assert not app.state.store.get("sources", source["id"]).get("deleted_at")
        assert wait_job(client, submitted["id"])["status"] == "completed"
        assert client.post("/api/sources/" + source["id"] + "/delete").status_code == 200


def test_source_delete_private_unassigned_restore_and_retained_files(deletion_client):
    client, app, settings = deletion_client
    source = attach(client, "aurora.txt", "Aurora checkpoint is Thursday.", ["hr"], shared=True)
    completed = submit(client, "hr", "Explain Aurora")
    stored = app.state.store.get("sources", source["id"])
    original = Path(stored["storage_path"])
    client.post("/api/agents/hr/delete")
    deleted = client.post("/api/sources/" + source["id"] + "/delete").json()
    assert deleted["deleted_at"] and deleted["shared"] is False
    assert client.get("/api/sources").json() == []
    assert client.get("/api/sources/deleted").json()[0]["id"] == source["id"]
    assert original.is_file() and original.read_text() == "Aurora checkpoint is Thursday."
    assert client.get("/api/jobs/" + completed["id"]).json() == completed
    assert client.get("/api/sources/" + source["id"]).status_code == 404
    assert client.post("/api/sources/" + source["id"] + "/refresh").status_code == 404
    assert client.post("/api/sources/" + source["id"] + "/access", json={"shared": True}).status_code == 404
    assert client.post("/api/assistant", json={"prompt": "Read Aurora", "source_ids": [source["id"]]}).status_code == 422
    assert client.post("/api/agents/finance/sources", json={"source_ids": [source["id"]]}).status_code == 422
    restored = client.post("/api/sources/" + source["id"] + "/restore").json()
    assert restored["deleted_at"] is None and restored["shared"] is False and restored["agent_ids"] == []
    assert restored["restoration_policy"] == "private_unassigned"
    agent = client.post("/api/agents/hr/restore").json()
    assert agent["source_ids"] == []
    assert app.state.knowledge.accessible_ids(agent) == []
    assert client.post("/api/agents/hr/sources", json={"source_ids": [source["id"]]}).status_code == 200
    assert submit(client, "hr", "Explain Aurora")["result"]["knowledge_found"] is True


def test_queued_assistant_source_revocation_does_not_reactivate_on_restore(deletion_client):
    client, app, settings = deletion_client
    source = attach(client, "aurora.txt", "Private Aurora secret checkpoint.", shared=True)
    app.state.store.put("agents", {"id": ASSISTANT_ID, "role": "custom", "name": "Assistant", "purpose": "Help with selected documents", "tools": ["read_knowledge"], "enabled": False, "status": "paused", "source": "", "source_ids": []})
    queued = client.post("/api/assistant", json={"prompt": "Explain Aurora", "source_ids": [source["id"]]}).json()
    assert client.post("/api/sources/" + source["id"] + "/delete").status_code == 200
    pending = app.state.store.get("jobs", queued["id"])
    assert pending["source_ids"] == [] and pending["metrics"]["revoked_source_ids"] == [source["id"]]
    client.post("/api/sources/" + source["id"] + "/restore")
    assistant = app.state.store.get("agents", ASSISTANT_ID)
    assistant["enabled"] = True
    app.state.store.put("agents", assistant)
    client.portal.call(app.state.scheduler.wake.set)
    completed = wait_job(client, queued["id"])
    assert completed["status"] == "completed" and completed["result"]["sources"] == []
    assert "deleted" in completed["result"]["answer"]
    assert client.post("/api/agents/" + ASSISTANT_ID + "/delete").status_code == 404
    assert client.post("/api/agents/" + ASSISTANT_ID + "/restore").status_code == 404


def test_capacity_counts_active_agents_and_restore_refuses_full_workspace(deletion_client):
    client, app, settings = deletion_client
    client.post("/api/agents/hr/delete")
    config = {"name": "Custom", "role": "custom", "purpose": "Read our own project documents", "tools": ["read_knowledge"]}
    for _ in range(26):
        assert client.post("/api/agents", json=config).status_code == 201
    assert len(client.get("/api/agents").json()) == 30
    assert client.post("/api/agents/hr/restore").status_code == 409
    assert app.state.store.get("agents", "hr")["deleted_at"]
    removable = next(agent for agent in client.get("/api/agents").json() if agent["role"] == "custom")
    client.post("/api/agents/" + removable["id"] + "/delete")
    assert client.post("/api/agents/hr/restore").status_code == 200


def test_supervision_identities_delete_without_disabling_enforcement(deletion_client):
    client, app, settings = deletion_client
    for identity in ["security", "optimizer"]:
        assert client.post("/api/agents/" + identity + "/delete").status_code == 200
    system = client.get("/api/system").json()
    assert system["security"]["allowlisted_tools_only"] is True
    assert client.post("/api/security/demo").json()["blocked"] is True
    assert client.post("/api/optimizer/approve", json={"policy": "priority", "approved": False}).status_code == 403
    assert client.post("/api/optimizer/approve", json={"policy": "priority", "approved": True}).json()["approved"] is True
    assert "security" not in {agent["id"] for agent in client.get("/api/agents").json()}
    assert "optimizer" not in {agent["id"] for agent in client.get("/api/agents").json()}
    assert client.post("/api/security/demo", json={"agent_id": "security"}).status_code == 404


async def test_source_refresh_and_delete_serialized_without_resurrection(tmp_path, monkeypatch):
    from app import knowledge_extract
    store = Store(tmp_path / "state.db")
    library = KnowledgeLibrary(store, Settings(upload_dir=tmp_path / "uploads"), EventBus(store))
    store.put("sources", {"id": "remote", "name": "Remote", "kind": "api", "url": "https://example.com/api", "status": "ready", "text": "Cached text", "shared": True, "refresh_minutes": 5, "metadata": {}})
    started, release = asyncio.Event(), asyncio.Event()
    async def fetch(url, headers=None):
        started.set()
        await release.wait()
        return {"text": "New text", "mime_type": "text/plain", "status": "ready", "error": None, "metadata": {}}
    monkeypatch.setattr(knowledge_extract, "fetch_source", fetch)
    refreshing = asyncio.create_task(library.refresh(store.get("sources", "remote")))
    await started.wait()
    deleting = asyncio.create_task(library.delete("remote"))
    await asyncio.sleep(0)
    assert not deleting.done()
    release.set()
    await refreshing
    deleted = await deleting
    assert deleted["deleted_at"] and library.list() == []
    assert store.get("sources", "remote")["text"] == "New text"
    with pytest.raises(KnowledgeError):
        await library.refresh(store.get("sources", "remote"))
    store.close()


async def test_delete_later_due_source_during_earlier_refresh_keeps_background_work_alive(tmp_path, monkeypatch):
    from app import knowledge_extract
    store = Store(tmp_path / "state.db")
    library = KnowledgeLibrary(store, Settings(upload_dir=tmp_path / "uploads"), EventBus(store))
    for identity in ["first", "later"]:
        store.put("sources", {"id": identity, "name": identity, "kind": "api", "url": "https://example.com/" + identity, "status": "ready", "text": "Cached text", "shared": True, "refresh_minutes": 5, "metadata": {}, "last_attempted_at": "2020-01-01T00:00:00+00:00"})
    started, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def fetch(url, headers=None):
        calls.append(url)
        if url.endswith("first"):
            started.set()
            await release.wait()
        return {"text": "New text", "mime_type": "text/plain", "status": "ready", "error": None, "metadata": {}}
    monkeypatch.setattr(knowledge_extract, "fetch_source", fetch)
    due = asyncio.create_task(library.refresh_due())
    await started.wait()
    await library.delete("later")
    release.set()
    await due
    assert calls == ["https://example.com/first"]
    first = store.get("sources", "first")
    first["last_attempted_at"] = "2020-01-01T00:00:00+00:00"
    store.put("sources", first)
    await library.refresh_due()
    assert calls == ["https://example.com/first", "https://example.com/first"]
    store.close()


def test_scheduler_excludes_deleted_and_missing_agents_and_recovery_cancels(tmp_path):
    queued = queued_job("hr")
    assert select_next([queued], "fifo", [{"id": "hr", "enabled": True, "deleted_at": "then"}]) is None
    assert select_next([queued], "fifo", []) is None
    store = Store(tmp_path / "state.db")
    agent = store.get("agents", "hr")
    agent["deleted_at"] = "then"
    store.put("agents", agent)
    store.put("jobs", queued)
    store.recover_interrupted_jobs()
    assert store.get("jobs", queued["id"])["status"] == "error"
    store.close()

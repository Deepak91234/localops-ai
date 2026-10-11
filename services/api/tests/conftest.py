from pathlib import Path
import json
from app.config import PROJECT_ROOT

FIXTURES = PROJECT_ROOT / "project-materials" / "archived-demo-data"


def attach(client, filename, text, agents=None, shared=False):
    response = client.post("/api/sources/upload", data={"name": filename, "description": "Explicit test document", "shared": str(shared).lower(), "agent_ids": json.dumps(agents or [])}, files={"file": (filename, text, "application/octet-stream")})
    assert response.status_code == 201, response.text
    return response.json()


def attach_fixtures(client):
    for filename, agent in [("handbook.txt", "hr"), ("invoices.csv", "finance"), ("support_playbook.txt", "support")]:
        attach(client, filename, (FIXTURES / filename).read_bytes(), [agent])

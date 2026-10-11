import json
import sqlite3
import threading
from pathlib import Path
from .agents import DEFAULT_AGENTS
from .models import utc_now


class Store:
    """One local SQLite database; JSON records retain inspectable workflow evidence."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.lock = threading.RLock()
        for table in ("agents", "jobs", "events", "settings", "sources"):
            self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.connection.commit()
        for agent in DEFAULT_AGENTS:
            if self.get("agents", agent["id"]) is None:
                self.put("agents", {**agent, "enabled": True, "created_at": utc_now(), "last_activity_at": None})
        # Backfill control fields only. Existing sources, job records, and history
        # remain intact; an unknown legacy creation date is never invented.
        for agent in self.all("agents"):
            if "enabled" not in agent:
                self.put("agents", {**agent, "enabled": True, "created_at": agent.get("created_at"), "last_activity_at": agent.get("last_activity_at")})
        if self.get("settings", "scheduler") is None:
            self.put("settings", {"id": "scheduler", "policy": "fifo"})

    def get(self, table: str, key: str):
        self._table(table)
        with self.lock:
            row = self.connection.execute(f"SELECT payload FROM {table} WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, table: str):
        self._table(table)
        with self.lock:
            rows = self.connection.execute(f"SELECT payload FROM {table} ORDER BY rowid", ()).fetchall()
        return [json.loads(row[0]) for row in rows]

    def active(self, table: str):
        return [record for record in self.all(table) if not record.get("deleted_at")]

    def delete_agent(self, agent):
        """Commit the tombstone and queued-job cancellation together."""
        stamp = utc_now()
        agent.update(deleted_at=stamp, enabled_before_delete=agent.get("enabled", True), enabled=False, status="paused", pause_pending=False)
        cancelled = []
        with self.lock, self.connection:
            self.connection.execute("UPDATE agents SET payload=? WHERE id=?", (json.dumps(agent, ensure_ascii=False), agent["id"]))
            for job in self.all("jobs"):
                if job["agent_id"] == agent["id"] and job["status"] == "queued":
                    job.update(status="error", error="Agent was deleted before this queued task started. Restore the agent and submit a new task if needed.", completed_at=stamp)
                    job.setdefault("metrics", {})["cancelled_by_agent_deletion"] = True
                    self.connection.execute("UPDATE jobs SET payload=? WHERE id=?", (json.dumps(job, ensure_ascii=False), job["id"]))
                    cancelled.append(job)
        return cancelled

    def delete_source(self, source):
        """Atomically revoke bindings and pending selections with the tombstone."""
        identity = source["id"]
        source.update(deleted_at=utc_now(), shared=False)
        changed_jobs = []
        with self.lock, self.connection:
            self.connection.execute("UPDATE sources SET payload=? WHERE id=?", (json.dumps(source, ensure_ascii=False), identity))
            for agent in self.all("agents"):
                if identity in agent.get("source_ids", []):
                    agent["source_ids"] = [key for key in agent["source_ids"] if key != identity]
                    self.connection.execute("UPDATE agents SET payload=? WHERE id=?", (json.dumps(agent, ensure_ascii=False), agent["id"]))
            for job in self.all("jobs"):
                if job["status"] == "queued" and identity in job.get("source_ids", []):
                    job["source_ids"] = [key for key in job["source_ids"] if key != identity]
                    revoked = job.setdefault("metrics", {}).setdefault("revoked_source_ids", [])
                    if identity not in revoked:
                        revoked.append(identity)
                    self.connection.execute("UPDATE jobs SET payload=? WHERE id=?", (json.dumps(job, ensure_ascii=False), job["id"]))
                    changed_jobs.append(job)
        return changed_jobs

    def put(self, table: str, record: dict):
        self._table(table)
        with self.lock:
            self.connection.execute(f"INSERT INTO {table}(id,payload) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (record["id"], json.dumps(record, ensure_ascii=False)))
            self.connection.commit()

    def recover_interrupted_jobs(self):
        deleted = {agent["id"] for agent in self.all("agents") if agent.get("deleted_at")}
        for job in self.all("jobs"):
            if job.get("agent_id") in deleted and job["status"] in {"running", "queued"}:
                job.update(status="error", error="Agent was deleted before work could finish. Submit a new task after restoring it.", completed_at=utc_now())
                job.setdefault("metrics", {})["cancelled_by_agent_deletion"] = True
                self.put("jobs", job)
                continue
            if job["status"] == "running":
                job.update(status="queued", started_at=None, completed_at=None, error=None)
                job["metrics"]["recovered_after_restart"] = True
                self.put("jobs", job)

    def migrate_source_bindings(self):
        """Remove legacy demo bindings; preserve names, purposes and immutable jobs."""
        legacy = {"handbook.txt", "invoices.csv", "support_tickets.json", "support_playbook.txt", "injection_policy.txt", "scheduler_microbenchmark"}
        for agent in self.all("agents"):
            if "source_ids" not in agent or agent.get("source") in legacy:
                agent.update(source="", source_ids=agent.get("source_ids", []))
                self.put("agents", agent)

    @staticmethod
    def _table(table):
        if table not in {"agents", "jobs", "events", "settings", "sources"}:
            raise ValueError("Invalid storage table")

    def close(self):
        self.connection.close()

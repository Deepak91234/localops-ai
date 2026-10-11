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
        for table in ("agents", "jobs", "events", "settings"):
            self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.connection.commit()
        for agent in DEFAULT_AGENTS:
            if self.get("agents", agent["id"]) is None:
                self.put("agents", agent)
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

    def put(self, table: str, record: dict):
        self._table(table)
        with self.lock:
            self.connection.execute(f"INSERT INTO {table}(id,payload) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (record["id"], json.dumps(record, ensure_ascii=False)))
            self.connection.commit()

    def recover_interrupted_jobs(self):
        for job in self.all("jobs"):
            if job["status"] == "running":
                job.update(status="queued", started_at=None, completed_at=None, error=None)
                job["metrics"]["recovered_after_restart"] = True
                self.put("jobs", job)

    @staticmethod
    def _table(table):
        if table not in {"agents", "jobs", "events", "settings"}:
            raise ValueError("Invalid storage table")

    def close(self):
        self.connection.close()

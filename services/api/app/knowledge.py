"""Durable user-owned knowledge, explicit access, and bounded local retrieval."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
import os
from uuid import uuid4
from .models import utc_now

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TEXT_LENGTH = 200_000
ASSISTANT_ID = "__assistant__"


class KnowledgeError(ValueError):
    pass


class KnowledgeConflict(KnowledgeError):
    pass


class KnowledgeLibrary:
    def __init__(self, store, settings, events):
        self.store, self.settings, self.events = store, settings, events
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.locks = {}
        self.refresh_task = None

    def agents(self):
        return [agent for agent in self.store.active("agents") if agent["id"] != ASSISTANT_ID]

    def validate_agents(self, ids):
        if len(ids) != len(set(ids)):
            raise KnowledgeError("Agent IDs must be unique.")
        valid = {agent["id"] for agent in self.agents()}
        if any(identity not in valid for identity in ids):
            raise KnowledgeError("An assigned agent does not exist.")

    def validate_sources(self, ids):
        if len(ids) != len(set(ids)):
            raise KnowledgeError("Source IDs must be unique.")
        if any((source := self.store.get("sources", identity)) is None or source.get("deleted_at") for identity in ids):
            raise KnowledgeError("An assigned source does not exist.")

    def metadata(self, source, detail=False):
        public = {key: source.get(key) for key in ("id", "name", "kind", "filename", "mime_type", "url", "status", "description", "bytes", "shared", "last_synced_at", "error", "refresh_minutes")}
        public["auth_configured"] = bool(source.get("auth_configured"))
        public["deleted_at"] = source.get("deleted_at")
        public["restoration_policy"] = "private_unassigned"
        public["restoration_note"] = "Restored sources are private and unassigned. Share them or assign them again to grant agents access."
        public["last_attempted_at"] = source.get("last_attempted_at")
        info = source.get("metadata", {})
        public["truncated"] = bool(info.get("truncated") or info.get("text_truncated") or info.get("csv_complete") is False)
        public["cached"] = bool(source.get("text") and source.get("status") != "ready")
        notes = []
        if public["truncated"]:
            notes.append(info.get("ocr_note") or "Extraction is partial; some pages, rows, or text exceed the reading limits.")
        if info.get("ocr"):
            notes.append("Text was read with local OCR and may contain recognition errors.")
        if public["cached"]:
            notes.append("Using the last successful cached text while refresh is pending or failed.")
        public["reading_note"] = " ".join(notes) or None
        public["text_length"] = len(source.get("text", ""))
        public["agent_ids"] = [agent["id"] for agent in self.agents() if source["id"] in agent.get("source_ids", [])]
        if detail:
            public.update(text_preview=source.get("text", "")[:12_000], metadata=source.get("metadata", {}), preview_truncated=len(source.get("text", "")) > 12_000)
        return public

    def list(self):
        return [self.metadata(source) for source in self.store.active("sources")]

    def accessible_ids(self, agent):
        if agent.get("deleted_at"):
            return []
        assigned = set(agent.get("source_ids", []))
        return [source["id"] for source in self.store.active("sources") if source.get("shared") or source["id"] in assigned]

    def documents(self, agent, job):
        if agent.get("deleted_at"):
            return []
        # Source selection is snapshotted when queued. A later revocation also
        # applies to queued business work; documents never expand permissions.
        selected = job.get("source_ids", self.accessible_ids(agent))
        allowed = set(selected) if agent["id"] == ASSISTANT_ID else set(self.accessible_ids(agent))
        return [source for identity in selected if identity in allowed and (source := self.store.get("sources", identity)) is not None and not source.get("deleted_at") and source.get("text") and (source.get("status") == "ready" or source.get("last_synced_at"))]

    def assign_agent(self, agent, source_ids):
        if agent.get("deleted_at"):
            raise KnowledgeError("Restore the agent before assigning knowledge.")
        self.validate_sources(source_ids)
        agent.update(source_ids=list(source_ids), source="")
        self.store.put("agents", agent)
        return agent

    def set_access(self, source, shared, agent_ids):
        latest = self.store.get("sources", source["id"])
        if latest is None or latest.get("deleted_at"):
            raise KnowledgeError("Restore the source before changing access.")
        source = latest
        self.validate_agents(agent_ids)
        source["shared"] = shared
        self.store.put("sources", source)
        for agent in self.agents():
            ids = [identity for identity in agent.get("source_ids", []) if identity != source["id"]]
            if agent["id"] in agent_ids:
                ids.append(source["id"])
            self.assign_agent(agent, ids)
        return self.metadata(source)

    async def changed(self):
        await self.events.publish("sources_updated", self.list())
        await self.events.publish("agents_updated", self.agents())

    @staticmethod
    def apply_extraction(source, extracted):
        text = extracted.get("text") or ""
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
            extracted.setdefault("metadata", {})["text_truncated"] = True
        status = extracted.get("status", "error")
        error = extracted.get("error")
        if status == "ready" and not text.strip():
            status, error = "stored", "Stored successfully, but no searchable text was extracted."
        source.update(status=status, error=error, last_attempted_at=utc_now())
        if status == "ready":
            source.update(text=text, mime_type=extracted.get("mime_type"), metadata=extracted.get("metadata", {}), last_synced_at=utc_now())
        elif not source.get("text"):
            source.update(text=text, mime_type=extracted.get("mime_type"), metadata=extracted.get("metadata", {}), last_synced_at=None)
        if source.get("bytes") is None:
            source["bytes"] = extracted.get("metadata", {}).get("bytes")
        return source

    async def upload(self, upload, name, description, shared, agent_ids):
        from .knowledge_extract import extract_file
        self.validate_agents(agent_ids)
        identity = str(uuid4())
        filename = Path((upload.filename or "uploaded-file").replace("\\", "/")).name[:200]
        suffix = Path(filename).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
            suffix = ".bin"
        path = self.settings.upload_dir / (identity + suffix)
        length = 0
        try:
            with path.open("xb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    length += len(chunk)
                    if length > MAX_FILE_BYTES:
                        raise KnowledgeError("Files must be at most 25 MB.")
                    destination.write(chunk)
            extracted = await asyncio.to_thread(extract_file, path, filename)
            self.validate_agents(agent_ids)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()
        source = {"id": identity, "name": name, "kind": "file", "filename": filename, "url": None, "description": description, "bytes": length, "shared": shared, "refresh_minutes": 0, "storage_path": str(path), "created_at": utc_now()}
        self.apply_extraction(source, extracted)
        self.store.put("sources", source)
        self.set_access(source, shared, agent_ids)
        await self.changed()
        return self.metadata(source)

    async def link(self, config):
        from .knowledge_extract import fetch_source
        self.validate_agents(config.agent_ids)
        if config.refresh_minutes and config.refresh_minutes < 5:
            raise KnowledgeError("Automatic refresh is disabled at zero, or must be at least five minutes.")
        identity = str(uuid4())
        token = config.api_token.get_secret_value() if config.api_token is not None else None
        extracted = await fetch_source(config.url, headers={"Authorization": "Bearer " + token} if token else None)
        self.validate_agents(config.agent_ids)
        extracted = self.redact_extraction(extracted, token)
        source = {"id": identity, "name": config.name, "kind": config.kind, "url": config.url, "filename": None, "description": config.description, "bytes": None, "shared": config.shared, "refresh_minutes": config.refresh_minutes, "created_at": utc_now(), "auth_configured": bool(token)}
        for field in ("name", "url", "description"):
            source[field] = self.redact(source[field], token)
        if token:
            folder = self.settings.upload_dir / "credentials"
            folder.mkdir(mode=0o700, parents=True, exist_ok=True)
            folder.chmod(0o700)
            descriptor = os.open(folder / (identity + ".token"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as destination:
                destination.write(token)
        self.apply_extraction(source, extracted)
        self.store.put("sources", source)
        self.set_access(source, config.shared, config.agent_ids)
        await self.changed()
        return self.metadata(source)

    @staticmethod
    def redact(value, token):
        if not token:
            return value
        if isinstance(value, str):
            return value.replace(token, "[REDACTED]")
        if isinstance(value, dict):
            return {key: KnowledgeLibrary.redact(item, token) for key, item in value.items()}
        if isinstance(value, list):
            return [KnowledgeLibrary.redact(item, token) for item in value]
        return value

    @staticmethod
    def redact_extraction(extracted, token):
        # Public status/type identifiers are protocol values, not secret echoes.
        # A short token such as "ready" must not corrupt the source state.
        return {**extracted, **{key: KnowledgeLibrary.redact(extracted.get(key), token) for key in ("text", "error", "metadata")}}

    async def refresh(self, source):
        from .knowledge_extract import extract_file, fetch_source
        lock = self.locks.setdefault(source["id"], asyncio.Lock())
        async with lock:
            # Reload after waiting: sharing changes made in the meantime survive.
            source = self.store.get("sources", source["id"])
            if source is None or source.get("deleted_at"):
                raise KnowledgeError("Source is deleted. Restore it before refreshing.")
            source["status"] = "refreshing"
            self.store.put("sources", source)
            await self.changed()
            token = None
            try:
                if source["kind"] == "file":
                    extracted = await asyncio.to_thread(extract_file, Path(source["storage_path"]), source["filename"])
                else:
                    if source.get("auth_configured"):
                        token = (self.settings.upload_dir / "credentials" / (source["id"] + ".token")).read_text()
                    extracted = await fetch_source(source["url"], headers={"Authorization": "Bearer " + token} if token else None)
                latest = self.store.get("sources", source["id"])
                if latest is None or latest.get("deleted_at"):
                    raise KnowledgeError("Source was deleted while refreshing.")
                self.apply_extraction(latest, self.redact_extraction(extracted, token))
            except Exception as exc:
                latest = self.store.get("sources", source["id"])
                if latest is None or latest.get("deleted_at"):
                    raise KnowledgeError("Source was deleted while refreshing.") from exc
                latest.update(status="error", error=self.redact(str(exc), token), last_attempted_at=utc_now())
            self.store.put("sources", latest)
            await self.changed()
            return self.metadata(latest)

    async def delete(self, identity):
        if any(job["status"] == "running" and identity in job.get("source_ids", []) for job in self.store.all("jobs")):
            raise KnowledgeConflict("A running task uses this source. Wait for it to finish before deleting it.")
        lock = self.locks.setdefault(identity, asyncio.Lock())
        async with lock:
            source = self.store.get("sources", identity)
            if source is None:
                raise KnowledgeError("Source not found.")
            if source.get("deleted_at"):
                return self.metadata(source)
            if any(job["status"] == "running" and identity in job.get("source_ids", []) for job in self.store.all("jobs")):
                raise KnowledgeConflict("A running task uses this source. Wait for it to finish before deleting it.")
            changed_jobs = self.store.delete_source(source)
            for job in changed_jobs:
                await self.events.publish("job_updated", job)
            await self.changed()
            return self.metadata(source)

    async def restore(self, identity):
        lock = self.locks.setdefault(identity, asyncio.Lock())
        async with lock:
            source = self.store.get("sources", identity)
            if source is None:
                raise KnowledgeError("Source not found.")
            if source.get("deleted_at"):
                source.update(deleted_at=None, restored_at=utc_now(), shared=False)
                self.store.put("sources", source)
                await self.changed()
            return self.metadata(source)

    async def refresh_due(self):
        for source in self.store.active("sources"):
            interval = source.get("refresh_minutes", 0)
            if source["kind"] == "file" or interval < 5:
                continue
            last = source.get("last_attempted_at") or source.get("last_synced_at")
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() if last else float("inf")
            if elapsed >= interval * 60:
                latest = self.store.get("sources", source["id"])
                if latest is None or latest.get("deleted_at"):
                    continue
                try:
                    await self.refresh(latest)
                except KnowledgeError:
                    # A source can be deleted while an earlier source is being
                    # refreshed; that must not stop refreshes of other sources.
                    continue

    async def _refresh_loop(self):
        while True:
            await asyncio.sleep(30)
            await self.refresh_due()

    def start(self):
        for source in self.store.active("sources"):
            if source.get("status") == "refreshing":
                source.update(status="error", error="The previous refresh was interrupted. Cached text is retained; refresh again to update the source.", last_attempted_at=utc_now())
                self.store.put("sources", source)
        self.refresh_task = asyncio.create_task(self._refresh_loop(), name="knowledge-auto-refresh")

    async def stop(self):
        if self.refresh_task:
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass


STOP_WORDS = set("a an the and in of for to do does is are can could would should how what which when where why who many please tell me about from with this that my our your their employees employee receive provide policy policies question answer explain document documents source sources attached knowledge company business summarize summary overview review list draft helpful reply customer client support safely information request need want use recommend recommended recommendations based selected records cite citations insights".split())


def retrieve_knowledge(documents, question, limit=6):
    """FTS5-ranked passages from stored extracted text, with genuine provenance."""
    chunks = []
    for source in documents:
        pages = re.split(r"(?m)^\s*\[?Page\s+(\d+)\]?\s*\n", source["text"])
        entries = [(1, source["text"])] if len(pages) == 1 else [(int(pages[index]), pages[index + 1]) for index in range(1, len(pages) - 1, 2)]
        for page, text in entries:
            for offset in range(0, len(text), 1400):
                snippet = text[offset:offset + 1600].strip()
                if snippet:
                    chunks.append({"source_id": source["id"], "document": source.get("filename") or source["name"], "name": source["name"], "page": page, "snippet": snippet, "url": source.get("url"), "kind": source["kind"], "cached": source.get("status") != "ready", "last_synced_at": source.get("last_synced_at")})
    if not chunks:
        return []
    terms = list(dict.fromkeys(term for term in re.findall(r"[\w-]+", question.lower()) if len(term) > 1 and term not in STOP_WORDS))[:30]
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE VIRTUAL TABLE passages USING fts5(content, tokenize='porter unicode61')")
        connection.executemany("INSERT INTO passages(content) VALUES (?)", [(chunk["snippet"],) for chunk in chunks])
        if terms:
            query = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
            rows = connection.execute("SELECT rowid FROM passages WHERE passages MATCH ? ORDER BY bm25(passages),rowid LIMIT ?", (query, limit)).fetchall()
            selected = [chunks[row[0] - 1] for row in rows]
        else:
            selected = []
        broad_intent = re.search(r"\b(summariz\w*|summary|overview|recommend\w*|review|insights)\b", question, re.IGNORECASE)
        if not selected and (not terms or broad_intent):
            # First passage of every selected document before extra passages from
            # a long file. This is bounded evidence sampling, never an exhaustive
            # review of every row or page in an arbitrary knowledge library.
            seen = set()
            first, remaining = [], []
            for chunk in chunks:
                (remaining if chunk["source_id"] in seen else first).append(chunk)
                seen.add(chunk["source_id"])
            selected = (first + remaining)[:limit]
    return [{"id": str(index), **chunk} for index, chunk in enumerate(selected, 1)]

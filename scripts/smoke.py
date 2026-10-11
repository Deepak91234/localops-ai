#!/usr/bin/env python3
"""Read-only loopback API, SSE, and production asset contracts; no job submissions."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
STATUSES = {"idle", "queued", "running", "completed", "error", "blocked", "paused"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class EntryAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.paths.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.paths.append(values["href"])


def run(output):
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "mode": "read-only GET contracts; no user-data mutation or inference submission",
        "offline_wan_test": "not performed",
        "checks": [],
    }
    try:
        with httpx.Client(base_url=BASE, timeout=15, trust_env=False, follow_redirects=False) as client:
            def get(path):
                response = client.get(path)
                response.raise_for_status()
                return response.json()

            health = get("/api/health")
            require(health.get("status") == "ok", "API health is not ok")
            require(health.get("synthetic_data") is False, "Health must report user-source mode")
            require(health.get("local_inference", {}).get("available") is True, "Local inference is unavailable")
            require(health.get("scheduler_policy") in {"fifo", "priority"}, "Invalid queue policy")
            report["health"] = {"status": health["status"], "synthetic_data": False, "local_model": health["local_inference"].get("model"), "local_inference_available": True, "scheduler_policy": health["scheduler_policy"]}
            report["checks"].append("health and existing local inference availability")

            agents, sources, jobs = get("/api/agents"), get("/api/sources"), get("/api/jobs?limit=500")
            require(all(isinstance(value, list) for value in (agents, sources, jobs)), "List API contract failed")
            agent_ids = [agent.get("id") for agent in agents]
            source_ids = [source.get("id") for source in sources]
            require(all(isinstance(identity, str) and identity for identity in agent_ids + source_ids), "Missing identity")
            require(len(agent_ids) == len(set(agent_ids)) and len(source_ids) == len(set(source_ids)), "Duplicate identities")
            require("__assistant__" not in agent_ids and len(agents) <= 30, "Visible workforce contract failed")
            categories = get("/api/categories")
            require(isinstance(categories, list), "Category list contract failed")
            category_ids = [category.get("id") for category in categories]
            require(len(category_ids) == len(set(category_ids)), "Duplicate category identities")
            require(all(isinstance(category.get("name"), str) and isinstance(category.get("color"), str) for category in categories), "Category display contract failed")
            for agent in agents:
                require(agent.get("category_id") in category_ids, "Agent has no persisted category")
                require(agent.get("status") in STATUSES and isinstance(agent.get("source_ids"), list), "Agent status/source contract failed")
                require(set(agent["source_ids"]).issubset(set(source_ids)), "Agent points to a missing source")
                insight = get(f"/api/agents/{agent['id']}/insights")
                require(isinstance(insight.get("workload"), dict) and isinstance(insight.get("sources"), list), "Agent insight contract failed")
            for source in sources:
                require(source.get("kind") in {"file", "url", "api"}, "Invalid source kind")
                require(source.get("status") in {"ready", "stored", "error", "refreshing"}, "Invalid source status")
                require(isinstance(source.get("shared"), bool) and isinstance(source.get("agent_ids"), list), "Source access contract failed")
                require(set(source["agent_ids"]).issubset(set(agent_ids)), "Source points to a missing agent")
                detail = get(f"/api/sources/{source['id']}")
                require(isinstance(detail.get("text_preview"), str) and len(detail["text_preview"]) <= 12_000, "Source preview contract failed")
                require(not ({"api_token", "token", "storage_path"} & set(detail)), "Private source internals exposed")
            for job in jobs:
                require(isinstance(job.get("id"), str) and job.get("status") in STATUSES and isinstance(job.get("metrics"), dict), "Job contract failed")
            report["state_counts"] = {"visible_agents": len(agents), "sources": len(sources), "returned_jobs": len(jobs), "completed_jobs": sum(job["status"] == "completed" for job in jobs)}
            report["checks"].append("agent identities, sources/access/previews, jobs, and all visible agent insights")
            report["checks"].append("durable category identities and complete workforce category assignment")

            system, metrics, activity = get("/api/system"), get("/api/metrics"), get("/api/activity")
            require(system.get("security", {}).get("binding") == "loopback-only" and system["security"].get("inference_local_only") is True, "Local boundary contract failed")
            require(isinstance(metrics.get("agents"), list) and isinstance(metrics.get("device"), dict) and isinstance(activity, list), "Monitoring contract failed")
            latest = get("/api/scenarios/latest")
            require(latest is None or isinstance(latest, dict), "Comparison read contract failed")
            report["checks"].append("system boundaries, metrics/activity, and saved comparison read")

            schema = get("/openapi.json")
            for path, method in (("/api/sources/upload", "post"), ("/api/sources/link", "post"), ("/api/sources/{source_id}/refresh", "post"), ("/api/sources/{source_id}/access", "post"), ("/api/agents/{agent_id}/sources", "post"), ("/api/assistant", "post"), ("/api/agents", "post"), ("/api/jobs", "post"), ("/api/categories", "post"), ("/api/agents/{agent_id}/category", "post"), ("/api/agents/{optimizer_id}/allocation-review", "post"), ("/api/agents/{agent_id}/delete", "post"), ("/api/sources/{source_id}/delete", "post")):
                require(method in schema.get("paths", {}).get(path, {}), f"Missing documented contract: {method} {path}")
            report["checks"].append("OpenAPI source, agent, and assistant command schemas (not executed)")

            with client.stream("GET", "/api/events") as response:
                response.raise_for_status()
                require("text/event-stream" in response.headers.get("content-type", ""), "SSE content type failed")
                event, snapshot, size = None, None, 0
                for line in response.iter_lines():
                    size += len(line)
                    require(size <= 2 * 1024 * 1024, "Initial SSE snapshot exceeds smoke bound")
                    if line.startswith("event: "):
                        event = line[7:]
                    elif line.startswith("data: ") and event == "snapshot":
                        snapshot = json.loads(line[6:])
                        break
                require(isinstance(snapshot, dict) and all(key in snapshot for key in ("agents", "sources", "jobs", "events", "metrics")), "Initial SSE snapshot missing")
                require({agent["id"] for agent in snapshot["agents"]} == set(agent_ids), "SSE workforce identities differ")
            report["checks"].append("initial live SSE snapshot (stream closed after reading)")

            dist = ROOT / "apps/web/dist"
            require((dist / "index.html").is_file(), "Production build missing; run bootstrap or npm build")
            response = client.get("/")
            response.raise_for_status()
            require("text/html" in response.headers.get("content-type", ""), "SPA content type failed")
            require(response.content == (dist / "index.html").read_bytes(), "Served SPA differs from local production build")
            entry = EntryAssets()
            entry.feed(response.text)
            require(bool(entry.paths) and all(path.startswith("/assets/") for path in entry.paths), "Entry scripts/styles must be local build assets")
            assets = sorted(path for path in (dist / "assets").iterdir() if path.suffix in {".js", ".css"})
            require(bool(assets), "No production JS/CSS assets")
            for asset in assets:
                served = client.get("/assets/" + asset.name)
                served.raise_for_status()
                require(served.content == asset.read_bytes(), "Served asset differs from local build")
            report["production_build"] = {"entry_sha256": hashlib.sha256(response.content).hexdigest(), "verified_js_css_assets": len(assets), "browser_execution_tested": False}
            report["checks"].append("served production HTML and all compiled JS/CSS match disk build")
        report["outcome"] = "passed"
        print(f"PASS: {len(report['checks'])} read-only contracts; {report['state_counts']['visible_agents']} visible agents, {report['state_counts']['sources']} sources, {report['state_counts']['completed_jobs']} completed jobs. No inference or application mutations submitted.")
    except Exception as error:
        report["outcome"] = "failed"
        report["error"] = str(error)
        print("FAIL: " + str(error), file=sys.stderr)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("Evidence: " + str(output))
    return 0 if report["outcome"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/evidence/read-only-smoke.json", help="summary path within this project (no source text or credentials)")
    options = parser.parse_args()
    output = (ROOT / options.output).resolve()
    require(output.is_relative_to(ROOT), "Evidence must remain within the project directory")
    return run(output)


if __name__ == "__main__":
    raise SystemExit(main())

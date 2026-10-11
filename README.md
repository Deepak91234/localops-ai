# LocalOps AI

**Your private AI workforce, in one living workspace.** A working local application for the ASUS GX10: a procedural 3D operations room, real Nemotron HR/Finance workflows, a durable job queue, inspectable evidence, scheduling measurements, and deterministic security gates. All bundled company data is fictional.

## Run on the verified GX10

Tested machine/runtime details are in [ACCESS_REPORT.md](docs/ACCESS_REPORT.md) and [LOCAL_INFERENCE_PROOF.md](docs/LOCAL_INFERENCE_PROOF.md): Ubuntu 24.04.4 ARM64, NVIDIA GB10, Python 3.12.3, Node 24.15.0, Ollama 0.23.2, and cached `nemotron3:33b`. No Docker or cloud inference is required.

From this project directory:

```bash
./scripts/bootstrap.sh
./scripts/service.sh start
```

Open **http://127.0.0.1:8000** in the GX10 browser. The API serves the built frontend from the same origin. Startup after setup is one command: `./scripts/service.sh start`. It returns after the API is ready and leaves the application running when this chat or terminal closes. The transient systemd user service lasts for the current user session; it is not enabled automatically after reboot. Services bind to loopback.

```bash
./scripts/service.sh status
./scripts/service.sh logs
./scripts/service.sh restart
./scripts/service.sh stop
```

Starting an already running service is safe and does not restart it. The script verifies the unit's project directory before managing it. Restart after changing `.env` or rebuilding the app. For foreground use, stop the service first, then run `./scripts/start.sh`; keep that terminal open and stop with Ctrl+C. Do not run both on port 8000 at once.

Before presenting, warm the actual local model:

```bash
.venv/bin/python scripts/prewarm.py
```

Observed runtime health tests took **57.714 seconds cold** and **0.609 seconds warm** for short prompts. These are two measured requests, not an application throughput claim. Ollama may unload the model after about five idle minutes; prewarm shortly before the demo. Application requests have a 180-second timeout and one inference request at a time.

Bootstrap installs project Python/npm dependencies using the included Python lock and npm lock, and builds local browser assets. It does not install a model, change GPU drivers, restart services, or expose a LAN port. Internet is needed for dependencies on first setup unless they are already cached. Python 3.11+ and a Node version supported by the installed Vite release are required; the versions above are the verified environment.

## Optional configuration and development

Defaults already match the working GX10 endpoint. For local overrides:

```bash
cp .env.example .env
```

Edit the plain values in `.env`; existing shell environment values take precedence. Startup reads only the supported configuration keys as literal data. The file is ignored by Git. Do not commit authentication keys. Hosted and LAN inference URLs are refused by the backend; use the installed Nemotron model.

```bash
./scripts/start.sh --dev
```

Stop the production service before development startup. Development frontend: http://127.0.0.1:5173, with `/api` proxied to http://127.0.0.1:8000. API reference: http://127.0.0.1:8000/docs. Stop the development script to stop both project processes.

## Try the complete workflow

1. Orbit or zoom the room, then click **People**. Ask “How many days of PTO do full-time employees receive?” The fictional handbook states **20 days on page 1**; inspect the returned snippet and model citation. Watch queued/running/completed status and the live activity stream.
2. Select **Finance** and analyze invoices. Inspect the exact Decimal calculations and source rows separately from the local model narrative. The fixture includes duplicate **INV-1001**. At the fixed demo date **2026-10-10**, raw overdue unpaid amount is **$4,950.50**; retaining the first row per invoice ID yields **$3,750.50**. Duplicate rows are flagged, never silently removed.
3. Select **Optimizer**, run FIFO vs priority, inspect both measured timelines, and approve a scheduling change. The comparison uses identical synthetic timed jobs; its queue wait measurement is not an inference or GPU speedup.
4. Select **Security**, run the controlled adversarial-document test, and inspect the refused `network.export` tool. No external request or data modification takes place.
5. Use **Monitor** for device-wide telemetry and job-level token/latency history. Create a constrained HR/Finance/Support agent in **Agent Studio**. The 2D view and reduced-motion control are available for accessibility and WebGL fallback.

See the [three-minute demo script](docs/DEMO_SCRIPT.md). Source selection uses the bundled fixtures; unrestricted business-document uploads and external integrations are outside this MVP.

## Verify and preserve evidence

```bash
(cd services/api && ../../.venv/bin/python -m pytest -q)
npm --prefix apps/web run build
curl --fail --silent http://127.0.0.1:8000/api/health
curl --fail --silent http://127.0.0.1:8000/api/jobs
```

Tests use explicit doubles for the model where appropriate, so passing unit tests alone does not prove real inference. The runtime proof above is from real local requests; full application results are recorded separately as they are observed. See [VERIFICATION.md](docs/VERIFICATION.md) for 31 passing tests, real application results and browser evidence, and [PROGRESS.md](docs/PROGRESS.md) for milestones.

With the local API running, repeat the full real-inference smoke test:

```bash
.venv/bin/python scripts/smoke.py
```

This submits only fictional tasks, measures the scheduler, runs the bounded security test, and saves `docs/evidence/live-smoke.json`.

State and activity history persist in `work/localops.sqlite3` by default. A fresh isolated demonstration can use a separate database without deleting history:

```bash
LOCALOPS_DB_PATH=work/fresh-demo.sqlite3 ./scripts/start.sh
```

## Architecture and limitations

React/TypeScript/Vite + React Three Fiber provide original procedural mascots and the room. FastAPI/Pydantic enforce configuration schemas, role/source/tool permissions, and loopback boundaries. SQLite persists agents, jobs, settings, and events. SSE keeps UI states linked to actual backend execution. HR retrieves locally with SQLite FTS5; Finance calculates deterministically; Ollama supplies the narrative.

[Architecture diagram](docs/ARCHITECTURE.md) · [Offline acceptance procedure](docs/OFFLINE_TEST.md).

GPU utilization, temperature, and power are device-wide NVIDIA-SMI samples. GB10 GPU memory counters return unavailable; per-agent numbers describe job/request timings and tokens, not physical GPU allocations. **WAN-disconnected operation has not yet been verified.** The offline procedure must be observed before making that claim.

This is a hackathon application, with local demonstration approvals rather than enterprise identity. Production authentication, multiuser isolation, advanced retrieval evaluation, external integrations, regulatory compliance, and robust process sandboxing remain future work. The model is never given arbitrary shell execution, network export, payment, or messaging tools.

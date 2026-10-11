# LocalOps AI

**Your private AI workforce, in one living workspace.** A working local application for the ASUS GX10: a procedural 3D operations room, separate identities and workspaces for every agent, real Nemotron HR/Finance/Support workflows, a durable job queue, inspectable evidence, measured recommendations, and deterministic security gates. All bundled company data is fictional.

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

1. Open **Living workspace** and explore the room. Every actual agent has its own physical character and name, including agents sharing the same role. **Create agent** adds a new identity and character immediately; the room supports up to 30 agents. **All agents** provides searchable access to the same identities. Use **Agent list**, **Reset camera**, and **Motion on/off** for accessibility or WebGL fallback.
2. Create a **Customer support** teammate named Avery, using **Customer support playbook**. Click its character or **Open agent** to open its full workspace. Agent pages remain available in the top workspace tabs. Each page has **Overview**, **Tasks**, **Test agent**, **Resources**, **Costs**, and **Suggestions**, scoped to that exact agent rather than its whole role.
3. In Avery's **Test agent** tab, choose **Account lockout**, **Billing question**, or **Team onboarding**, then **Generate local draft**. Inspect the real local model response and playbook evidence. The draft supports human review; it does not send a message, change an account, or initiate a payment. **Tasks** retains this agent's requests and results; **Resources** shows its measured timings and reported tokens.
4. Open Harper's **HR & policy** workspace and use **Test agent → PTO allowance → Ask local agent**. The fictional handbook states **20 days on page 1**; inspect the returned snippet and citation. **Remote work** and **Missing policy** provide additional grounded tests. Watch actual queued/running/completed states and team activity.
5. Open Finley's **Finance** workspace and choose **Test agent → Run invoice analysis**. Inspect exact Decimal calculations and source rows separately from the local model narrative. The fixture includes duplicate **INV-1001**. At the fixed demo date **2026-10-10**, raw overdue unpaid amount is **$4,950.50**; retaining the first row per invoice ID yields **$3,750.50**. Duplicate rows are flagged, never silently removed. Finance's **Overview** links its invoice evidence to the Optimizer's allocation review.
6. Open Orbit's **Optimizer** workspace. **Overview** lists every agent's measured workload, individual recommendations and reasons, and controls to **Approve pause** or **Resume**. Inspect supporting measurements before acting; running jobs finish safely and paused queues are retained. **Test agent → Run measured comparison** replays identical synthetic timed jobs through FIFO and priority. Inspect both wait times and approve a policy change explicitly. These results do not measure inference acceleration, physical GPU allocation, or dollar savings.
7. Open Sentinel's **Security** workspace. **Overview** shows past security events and enforced guardrails. **Test agent → Run controlled security test** refuses `network.export` deterministically; inspect the execution, network-request, and file-modification fields. **System monitor** shows device-wide telemetry and recent job timings separately from each agent's resource history.

**Costs** shows a dollar estimate only when an hourly rate is supplied. Its optional manual calculator uses recorded processing duration and your entered assumption; it does not configure the agent or charge anything. A configured bookkeeping estimate can use `LOCALOPS_HOURLY_RATE_USD` in `.env` followed by a service restart. Actual electricity bills, exclusive GPU shares, payments, and savings are not measured. Pausing an idle agent does not unload shared model weights.

See the [three-minute demo script](docs/DEMO_SCRIPT.md). Source selection uses the bundled fixtures; unrestricted business-document uploads and external integrations are outside this MVP.

## Verify and preserve evidence

```bash
(cd services/api && ../../.venv/bin/python -m pytest -q)
npm --prefix apps/web run build
curl --fail --silent http://127.0.0.1:8000/api/health
curl --fail --silent http://127.0.0.1:8000/api/jobs
```

The current backend suite passes **38 tests**. Tests use explicit doubles for the model where appropriate, so passing unit tests alone does not prove real inference. A browser walkthrough separately created Avery, observed the physical agent count increase from 11 to 12, and completed a real local Support request with a recorded 4.75-second timing and 1,001 reported tokens. That is one observed request, not a throughput promise. See [VERIFICATION.md](docs/VERIFICATION.md) for recorded application results and browser evidence, and [PROGRESS.md](docs/PROGRESS.md) for milestones.

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

React/TypeScript/Vite + React Three Fiber provide original procedural mascots, a separate body for every agent, and full agent workspaces with reusable animated portraits. FastAPI/Pydantic enforce configuration schemas, role/source/tool permissions, and loopback boundaries. SQLite persists identities, jobs, settings, and events. SSE keeps UI states linked to actual backend execution. HR retrieves locally with SQLite FTS5; Finance calculates deterministically; Support retrieves the fictional local playbook; Ollama supplies grounded responses. Agent insights derive recommendations and optional cost estimates from observed work, and deterministic controls enforce pause/resume and queue-policy approvals.

[Architecture diagram](docs/ARCHITECTURE.md) · [Offline acceptance procedure](docs/OFFLINE_TEST.md).

GPU utilization, temperature, and power are device-wide NVIDIA-SMI samples. GB10 GPU memory counters return unavailable; per-agent numbers describe job/request timings and tokens, not physical GPU allocations. **WAN-disconnected operation has not yet been verified.** The offline procedure must be observed before making that claim.

This is a hackathon application, with local demonstration approvals rather than enterprise identity. Production authentication, multiuser isolation, advanced retrieval evaluation, external integrations, regulatory compliance, and robust process sandboxing remain future work. The model is never given arbitrary shell execution, network export, payment, or messaging tools.

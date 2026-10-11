# LocalOps AI

**Your private AI workforce, in one living workspace.** A working local application for the ASUS GX10: original animated 3D agents, individual workspaces, reusable knowledge uploads and connections, real local Nemotron responses, a durable job queue, inspectable evidence, measured recommendations, and deterministic tool permissions. Normal agent answers use the knowledge you supply; archived handoff and earlier demonstration records are not automatically used.

Source repository: [Deepak91234/localops-ai](https://github.com/Deepak91234/localops-ai). See [setup on another device](docs/GITHUB_SETUP.md) for cloning and local runtime requirements. Uploaded documents and saved tasks stay on your own device.

## Run on the verified GX10

The project is at `/home/asus/Downloads/localops-ai`. Tested machine/runtime details are in [ACCESS_REPORT.md](docs/ACCESS_REPORT.md) and [LOCAL_INFERENCE_PROOF.md](docs/LOCAL_INFERENCE_PROOF.md): Ubuntu 24.04.4 ARM64, NVIDIA GB10, Python 3.12.3, Node 24.15.0, Ollama 0.23.2, and cached `nemotron3:33b`. No Docker or cloud inference is required.

From this project directory:

```bash
./scripts/bootstrap.sh
./scripts/service.sh start
```

Open **http://127.0.0.1:8000** in the GX10 browser. The API serves the built frontend from the same origin. After setup, `./scripts/service.sh start` returns when the API is ready and leaves the application running when this chat or terminal closes. The transient systemd user service lasts for the current user session; it is not enabled automatically after reboot. Services bind to loopback.

```bash
./scripts/service.sh status
./scripts/service.sh logs
./scripts/service.sh restart
./scripts/service.sh stop
```

Starting an already running service is safe and does not restart it. The script verifies the unit's project directory before managing it. Restart after changing `.env` or rebuilding the app. For foreground use, stop the service first, then run `./scripts/start.sh`; keep that terminal open and stop with Ctrl+C. Do not run both on port 8000 at once.

Before a presentation, warm the actual local model:

```bash
.venv/bin/python scripts/prewarm.py
```

Observed runtime checks took **57.714 seconds cold** and **0.609 seconds warm** for short prompts. These are two measured requests, not a throughput claim. Ollama may unload the model after about five idle minutes; prewarm shortly before presenting. Application requests have a 180-second timeout and one inference request at a time.

Bootstrap installs project Python/npm dependencies using the included locks and builds local browser assets. It does not install a model, change GPU drivers, restart services, or expose a LAN port. Internet is needed for first setup unless dependencies are cached. Python 3.11+ and a Node version supported by the installed Vite release are required; the versions above are the verified environment.

## Optional configuration and development

Defaults match the working GX10 endpoint. For local overrides:

```bash
cp .env.example .env
```

Edit plain values in `.env`; existing shell environment values take precedence. Startup reads only supported keys as literal data. The file is ignored by Git. Hosted and LAN inference URLs are refused by the backend; use the installed local model.

```bash
./scripts/start.sh --dev
```

Stop the production service before development startup. Development frontend: http://127.0.0.1:5173, with `/api` proxied to http://127.0.0.1:8000. API reference: http://127.0.0.1:8000/docs. Stopping the development script stops both project processes.

## Use your own knowledge

1. Open **Knowledge sources**. **Upload files** or **Link website or API** creates a reusable source with reading status, preview, access selection, and sync history. Share it with all current and future agents, assign selected agents, or leave it unassigned.
2. Choose **Create agent**, select **HR**, **Finance**, or **Other**, and enter its name and purpose. Select existing sources or upload/link them in the creation dialog. Every created agent gets a separate named character immediately, including multiple agents with the same role. The workspace supports up to 30 visible agents; the local assistant is separate.
3. Select a character or find the identity in **All agents**. Its full page has **Overview**, **Tasks**, **Test agent**, **Knowledge sources**, **Resources**, **Costs**, and **Suggestions**. Open pages remain accessible as top workspace tabs.
4. Click **Test agent**. The request form scrolls into view and receives focus immediately. Ask a question about the agent's sources, then inspect actual queued/running/completed states, model response, cited passages, and measured timings. Paused agents show an editable request and **Resume agent** action. An agent without searchable knowledge asks you to add it rather than substituting example business records.
5. Open **I can help you** at the bottom right for the local knowledge assistant. Shared searchable sources are selected initially; choose exactly which library sources to use, including private ones as the local workspace owner. Ask a summary or recommendation, then a follow-up. Recent conversation and the current selection accompany each request. An empty selection uses general local assistance without supplying business records.
6. Review the exact agent's **Tasks**, **Resources**, **Costs**, and **Suggestions**. **Optimizer** reviews recorded workloads with reasons and explicit pause/resume or queue-policy approval. **Security** shows enforced boundaries and prior events. Scheduler comparisons and security checks are labeled controlled test scenarios.

**Delete agents and sources:** Every agent card in **All agents** and the workspace list has a labeled **Delete** button; each agent page also has **Delete agent**. Each knowledge card has **Delete**. Confirm the action, use **Undo**, or restore it later from **Trash** in the sidebar. Deleting an agent removes its character and tabs, cancels queued jobs, and preserves history. Running jobs must finish first. Restored sources are private and unassigned; use **Manage access** to grant access again.

The centered **Living workspace** toolbar has **Reset camera**, **Agent list / 3D workspace**, and **Motion on/off**. **System monitor** shows shared GX10 readings separately from agent request metrics. See the [user guide](docs/USER_GUIDE.md) and [three-minute presentation script](docs/DEMO_SCRIPT.md).

### Supported source formats and connections

| Source | Implemented behavior and limits |
| --- | --- |
| Uploaded text | Text, Markdown, CSV, JSON, HTML, XML, YAML, and logs. Up to 25 MiB per file, labeled 25 MB in the UI; up to 200,000 indexed characters and a 12,000-character preview. |
| PDF | Text from at most the first 100 pages; PDFs over 250 pages are refused. PDFs with no extractable text use local OCR on the first five pages. Password-protected PDFs require an unlocked copy. Partial reading is shown. |
| Office and images | DOCX, XLSX, PPTX and common image formats. Office extraction reads stored text and cached cell values; it does not execute formulas, macros, or embedded programs. Images use local OCR, which can misread figures. Legacy DOC/XLS/PPT files require export to a supported format. |
| Other uploads | Saved with a clear unavailable/error status when no searchable text is extracted. Saving a file does not mean its contents were understood. |
| Website / read-only API | Public HTTP/HTTPS page text or API text/JSON, plus supported linked PDF content. Ports 80/443, 5 MiB response limit, 15-second fetch timeout. Private network addresses and embedded URL credentials are refused. Login sessions and JavaScript-rendered pages are not imported. |
| API authentication | Optional user-provided Bearer token over HTTPS only; authenticated requests do not follow redirects. Tokens stay in permission-restricted local files and are redacted from returned metadata and previews. Provider OAuth sign-in and managed account connectors are future work. |
| Refresh | Manual **Sync now**, or snapshots every 5 minutes, 15 minutes, or hour. Failed refreshes retain the last successful cached text and show the error. Inspect last successful sync and reading status; these are periodic snapshots, not streaming data. |

Finance can calculate exact invoice totals from a complete CSV ledger with unique columns `vendor,invoice_id,due_date,amount,status,category`, `YYYY-MM-DD` dates, paid/unpaid status, and non-negative amounts with at most two decimal places. Raw and first-record-per-ID totals remain separate, with duplicate source rows visible. Other financial documents use grounded question answering; model prose is not a verified spreadsheet calculation.

**Costs** shows an estimate only when an hourly rate is supplied. The manual calculator uses recorded processing duration and your assumption; a configured bookkeeping estimate can use `LOCALOPS_HOURLY_RATE_USD` in `.env` followed by restart. These are not payments, electricity bills, exclusive GPU shares, or measured savings. Pausing an agent holds work intake without unloading shared model weights.

## Verify and preserve evidence

```bash
(cd services/api && ../../.venv/bin/python -m pytest -q)
npm --prefix apps/web run build
.venv/bin/python scripts/smoke.py
```

The latest backend suite passed **107 tests**; strict TypeScript and the production build passed. Model doubles are used where appropriate, so automated checks alone do not prove inference. The smoke script performs read-only health/API/SSE/built-asset checks against the running loopback application and writes a summary; it creates no agents, sources, jobs, security events, or policy changes and does not generate an inference request.

Separate real-model evidence includes a custom agent answering **25 MB** and **React `^19.2.0`** from the uploaded product guide and frontend manifest, a private-source assistant recommendation and follow-up, and a public GitHub API source with successful **Sync now** and an observed automatic five-minute refresh. A subsequent API-only assistant answer matched the recorded value and sync timestamp. Earlier inference evidence retained 16 visible agents and three product/runtime sources. The latest read-only checkpoint observes 16 visible agents, six sources, and eight completed jobs; deletion QA preserved every pre-existing identity, source, and job. See [VERIFICATION.md](docs/VERIFICATION.md) for exact results and limits and [PROGRESS.md](docs/PROGRESS.md) for milestones.

Runtime records, indexed text, and source metadata persist in `work/localops.sqlite3`; uploaded originals and source credentials are under `work/knowledge`. Preserve both when backing up. For a separate workspace without deleting history, stop the existing service and run:

```bash
LOCALOPS_DB_PATH=work/fresh-workspace.sqlite3 ./scripts/start.sh
```

Archived handoff materials and earlier demonstration records remain in `project-materials` for recovery. They are not automatically assigned as agent knowledge.

`/home/asus/Downloads/LocalOps_AI_Project.zip` is the refreshed portable source/build bundle. It includes code, docs, built browser assets, and explicitly archived test fixtures. The live database, user uploads, credentials, `.env`, Python environment, and npm dependencies remain in the working project folder and are excluded from that ZIP. Use the folder above to continue with the current records; bootstrap the ZIP's extracted source for a fresh setup.

## Architecture and practical limits

React/TypeScript/Vite and React Three Fiber provide the procedural room, separate characters, and animated agent portraits. FastAPI/Pydantic enforce schemas, tool permissions, and loopback boundaries. SQLite persists identities, sources, jobs, settings, and events. SSE links UI states to real execution. Bounded local extraction and SQLite FTS5 retrieval supply evidence to the existing Ollama/Nemotron service. Finance uses exact Decimal calculations for supported ledgers; other business workflows and the assistant use selected source passages.

[Architecture](docs/ARCHITECTURE.md) · [Offline acceptance procedure](docs/OFFLINE_TEST.md) · [GitHub and other devices](docs/GITHUB_SETUP.md).

GPU utilization, temperature, and power are device-wide NVIDIA-SMI samples. GB10 memory counters are unavailable; per-agent metrics are request timings and reported tokens, not physical allocations. Retrieved citations identify evidence but do not guarantee that every generated statement is correct. Review advice, OCR output, partial extraction, and cached timestamps before acting.

**WAN-disconnected acceptance has not been observed.** Stored knowledge and local inference can operate without refreshing remote sources; remote connections need network access for new snapshots. Production authentication, multiuser isolation, provider OAuth integrations, advanced retrieval evaluation, and robust process sandboxing remain future work. Agent tools do not execute arbitrary shell commands, export records, send messages, or initiate payments; remote source fetching is an explicit owner-configured read-only action.

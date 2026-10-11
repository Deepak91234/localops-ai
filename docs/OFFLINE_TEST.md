# WAN-disconnected acceptance test

**Status: not yet observed.** The model, source data, backend, and browser build are local, and real loopback inference has passed. These facts alone do not prove the complete application works with WAN disconnected. Do not change this status without recording the actual test.

This procedure keeps loopback active. The user controls the WAN disconnect and reconnect; the agent has not changed network settings.

## Prepare while online

From the project directory:

```bash
./scripts/bootstrap.sh
(cd services/api && ../../.venv/bin/python -m pytest -q)
npm --prefix apps/web run build
.venv/bin/python scripts/prewarm.py
./scripts/start.sh
```

Use the built app at **http://127.0.0.1:8000**, not a hosted page. The existing Ollama model must already be cached. No bootstrap/package/model downloads should be needed during the offline phase.

## Observe with WAN unavailable

1. Disconnect the GX10's upstream internet connection using the user's chosen method while retaining localhost. Record the method and local time. Confirm an external site cannot load and the local app URL still loads.
2. Reload http://127.0.0.1:8000. Confirm the room or explicitly labeled 2D fallback renders; check browser developer tools for failed required external assets.
3. Ask People: “How many days of PTO do full-time employees receive?” Wait for a **new completed job**, generated after disconnection. Record job ID, model ID, answer, and page/snippet evidence. Expected handbook fact: **20 days**, page 1.
4. Run a **new Finance job**. Verify duplicate **INV-1001**, raw overdue **$4,950.50**, deduplicated overdue **$3,750.50**, and local model narrative. Record its job ID and timestamp.
5. Run the comparison and controlled security block. Check the live SSE stream still updates job/agent state.
6. In a second terminal, capture local proof without remote requests:

```bash
mkdir -p work/offline-evidence
curl --fail --silent http://127.0.0.1:8000/api/health > work/offline-evidence/health.json
curl --fail --silent http://127.0.0.1:8000/api/jobs > work/offline-evidence/jobs.json
curl --fail --silent http://127.0.0.1:8000/api/scenarios/latest > work/offline-evidence/comparison.json
.venv/bin/python scripts/prewarm.py > work/offline-evidence/local-inference.json
```

7. Restore WAN through the same user-controlled mechanism after recording the outcome. Preserve screenshots and the JSON evidence; do not remove existing job history.

## Result record

Fill only after observation:

| Field | Result |
| --- | --- |
| Date/time and observer | Not recorded |
| WAN disconnect method | Not recorded |
| External access failure observed | Not recorded |
| Local app reload / 3D render | Not recorded |
| HR new job ID / answer / source | Not recorded |
| Finance new job ID / correct totals | Not recorded |
| Local model ID / request result | Not recorded |
| SSE / scheduler / security | Not recorded |
| Limitations or failures | Not recorded |
| Acceptance outcome | **UNVERIFIED** |

A browser's cached previous answer is insufficient evidence. Both HR and Finance must create and complete new jobs while WAN is unavailable. A failed test should retain its actual failure and remain incomplete.

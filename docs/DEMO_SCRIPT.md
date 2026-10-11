# Three-minute LocalOps AI demonstration

Use only the bundled fictional Cedar & Coast records. Presenter opening: **“Run your business AI team on hardware you control, see what it is doing, and improve it safely.”**

## Before judges arrive

```bash
./scripts/start.sh
# In a second terminal, from the project directory:
.venv/bin/python scripts/prewarm.py
```

Open http://127.0.0.1:8000. Confirm the local connection indicator names `nemotron3:33b`. Keep the prewarm JSON available as real endpoint evidence. A cold request previously took 57.714 seconds; leave time for loading before the judged three minutes. Use a browser on the GX10; no LAN binding is required.

## Presentation sequence

| Time | Action | What the judge can inspect |
| --- | --- | --- |
| 0:00–0:25 | Reveal the room. Orbit, zoom, click an original mascot, reset the camera. | Five operational zones, animated characters, accessible HTML drawers. Mention the 2D view and motion control. |
| 0:25–0:55 | Click People; ask the default PTO question. | A real backend job moves from queued to running to completed. Nemotron answers **20 days**, with handbook page 1 and the source snippet. |
| 0:55–1:25 | Click Finance; analyze the invoice ledger. | Duplicate **INV-1001**; exact raw overdue **$4,950.50** and first-record deduplicated overdue **$3,750.50**, as of October 10, 2026. Show source rows and distinguish calculations from model narrative. |
| 1:25–2:00 | Click Optimizer; run baseline vs optimized; approve priority scheduling. | Actual measured queue waiting times for the same five synthetic timed jobs. Urgent support moves ahead of queued standard work; running work finishes safely. Approval changes the actual queue policy. |
| 2:00–2:25 | Click Security; run the controlled adversarial-document test. | `network.export` is deterministically refused. Inspect `executed:false`, `network_request_made:false`, and `files_modified:false`. |
| 2:25–3:00 | Open Monitor and show endpoint proof. | Device-wide GPU utilization/temperature/power, job tokens and latency, local model ID. Explain unavailable GPU memory and state offline verification status accurately. |

The optimizer's **Explain with local Nemotron** button is an optional extra real inference call. Its initial measured comparison needs no model and completes quickly. Never describe its synthetic service-duration benchmark as faster inference, saved money, or improved GPU efficiency.

## Contingencies

- **Cold model:** wait for the real request or prewarm again. Do not substitute a canned answer. Show the loading state, local endpoint evidence, and deterministic invoice source while loading.
- **Inference error:** inspect `/api/health`, run `scripts/prewarm.py`, and check the installed model with `curl http://127.0.0.1:11434/v1/models`. Existing errors remain inspectable in history. Do not claim the failed job completed.
- **WebGL unavailable:** use **2D list view**; all backend workflows and HTML results remain available. This is an accessibility fallback; judged 3D acceptance still needs a WebGL-capable browser.
- **Port occupied:** stop the earlier LocalOps process with Ctrl+C in its terminal. Do not kill an unrelated process or expose a new network port.
- **Offline question:** say “Inference and data are local; a full WAN-disconnected test is [verified with recorded evidence / not yet observed].” Only choose the first statement after completing [OFFLINE_TEST.md](OFFLINE_TEST.md).

Optional final action: create a named HR agent with `read_policy` and `handbook.txt` to show constrained configuration. Only allowlisted role/source/tool combinations are accepted.

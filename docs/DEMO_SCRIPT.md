# Three-minute LocalOps AI demonstration

Use only the bundled fictional Cedar & Coast records. Presenter opening: **“Run your business AI team on hardware you control, see what it is doing, and improve it safely.”**

## Before judges arrive

```bash
./scripts/service.sh start
.venv/bin/python scripts/prewarm.py
```

Open http://127.0.0.1:8000. Confirm the local connection indicator names `nemotron3:33b`. The service stays running after the terminal or chat closes for the current user session; it does not enable startup after reboot. Check it with `./scripts/service.sh status` and inspect failures with `./scripts/service.sh logs`. Foreground `./scripts/start.sh` is also available when its terminal stays open; stop the service first to free port 8000.

Keep the prewarm JSON available as real endpoint evidence. A cold request previously took 57.714 seconds; leave time for loading before the judged three minutes. Use a browser on the GX10; no LAN binding is required. Choose a fresh Support name, such as **Avery demo**, and identify Finley, Orbit, and Sentinel in **All agents** before presenting. Keep one idle teammate available for a reversible pause/resume demonstration.

If Harper has no saved PTO result, run **Test agent → PTO allowance → Ask local agent** before judges arrive, and retain the actual completed answer and page-1 source. Confirm Finley and the new Support agent are enabled before submitting their tasks.

## Presentation sequence

| Time | Action | What the judge can inspect |
| --- | --- | --- |
| 0:00–0:20 | Reveal **Living workspace**. Orbit and reset the camera. Click **Create agent**, choose **Customer support**, enter Avery demo, keep **Customer support playbook**, and create it. | The physical agent count increases by one and a separate named character appears. Duplicate-role teammates remain separate identities. |
| 0:20–1:00 | Click the new character or **Open agent**. Show its full workspace and top page tab. Choose **Test agent → Account lockout → Generate local draft**. | The actual job moves queued → running → completed. Inspect Nemotron's response and local playbook evidence. Show that **Tasks** and **Resources** belong to Avery alone. |
| 1:00–1:30 | Open Finley's **Finance** workspace. Choose **Test agent → Run invoice analysis**, then inspect the result and **Overview** evidence. | Duplicate **INV-1001**; exact raw overdue **$4,950.50** and first-record deduplicated overdue **$3,750.50**, as of October 10, 2026. Show source rows and distinguish exact calculations from model narrative. |
| 1:30–2:05 | Follow **Open measured Optimizer allocation** to Orbit. Inspect one agent's workload and recommendation reason. **Approve pause** for an idle teammate, then **Resume** it. In **Test agent**, run the measured comparison and inspect the queue policy approval. | Real per-agent counts, timings and reported tokens; explicit reversible controls. FIFO and priority use identical synthetic timed jobs. Running work finishes safely, and approval changes the actual policy. Finance evidence remains linked to the allocation review. |
| 2:05–2:35 | Open Sentinel's **Security** workspace. Show **Overview** past events and guardrails, then **Test agent → Run controlled security test**. | `network.export` is deterministically refused. Inspect `executed:false`, `network_request_made:false`, and `files_modified:false`. The event appears in real history. |
| 2:35–3:00 | Show **System monitor** and the local model ID. If time permits, open Harper's saved **Tasks** result for PTO and briefly show an agent's **Costs** tab. | Device-wide GPU utilization/temperature/power; per-request tokens and latency. HR evidence states **20 PTO days**, handbook page 1. Dollar estimates remain unavailable until a rate is supplied. State offline verification status accurately. |

The page sections are **Overview**, **Tasks**, **Test agent**, **Resources**, **Costs**, and **Suggestions**. Use the top workspace tabs to return to an agent without collapsing several identities into one role page. **All agents** is a searchable alternative to clicking a character; **Agent list** and **Motion on/off** are available in the room.

The optimizer's **Explain with Nemotron** button is an optional extra real inference call. Its measured comparison needs no model and completes quickly. **Suggestions** explains why each proposed action fits that agent's observed work. Never describe the synthetic service-duration benchmark as faster inference, saved money, or improved GPU efficiency. Pausing an idle agent does not unload shared model weights.

For **Costs**, supply a non-negative hourly assumption only if showing a manual estimate is useful. The calculation is measured processing seconds ÷ 3,600 × that rate. It is an estimate, not a bill, electricity reading, exclusive GPU allocation, or payment action. Queue time is excluded from the calculation.

Optional follow-up: open Harper's **Test agent**, choose **PTO allowance**, and **Ask local agent** to generate another real answer. Support also has **Billing question** and **Team onboarding** presets. All Support outputs are drafts for review; no message, account change, or payment is executed.

## Contingencies

- **Cold model:** wait for the real request or prewarm again. Do not substitute a canned answer. Show the loading state, local endpoint evidence, and deterministic invoice source while loading.
- **Inference error:** inspect `/api/health`, run `scripts/prewarm.py`, and check the installed model with `curl http://127.0.0.1:11434/v1/models`. Existing errors remain inspectable in history. Do not claim the failed job completed.
- **WebGL unavailable:** use **Agent list** or **All agents**; full agent pages, backend workflows, and results remain available. This is an accessibility fallback; judged 3D acceptance still needs a WebGL-capable browser.
- **App connection lost:** run `./scripts/service.sh status`, then `./scripts/service.sh start`. An already running owned service is reused without a restart. If it remains unavailable, inspect `./scripts/service.sh logs`.
- **Port occupied:** use `./scripts/service.sh stop` for the owned LocalOps service, or Ctrl+C in the terminal of an earlier foreground instance. Do not kill an unrelated process or expose a new network port.
- **Offline question:** say “Inference and data are local; a full WAN-disconnected test is [verified with recorded evidence / not yet observed].” Only choose the first statement after completing [OFFLINE_TEST.md](OFFLINE_TEST.md).

Only allowlisted role/source/tool combinations are accepted. The current backend suite has 38 passing tests; an observed Avery Support walkthrough separately increased the visible character count from 11 to 12 and completed real local inference with a recorded 4.75-second timing and 1,001 reported tokens. Present those as observed evidence, not guaranteed timings for the next request.

# Final application verification

Observed on the actual ASUS GX10 on October 10, 2026 (America/Los_Angeles). All company data is fictional.

## Automated checks

- 38 backend tests passed after agent insights, controls, and Support retrieval were added. One upstream Starlette TestClient deprecation warning; no failures.
- Strict TypeScript check and Vite production build passed.
- `scripts/bootstrap.sh` completed using the Python/npm locks; `scripts/start.sh` launched the production SPA/API at loopback port 8000.
- Prewarm redirects are refused; a local synthetic HTTP 302 test confirmed no external request. Environment files are parsed as literal configuration.

## Actual local inference jobs

| Workflow | Model | Request latency | Tokens | Observed result |
| --- | --- | ---: | ---: | --- |
| hr | nemotron3:33b | 868.52 ms | 504 | 20 PTO days, handbook page 1 and [1] citation |
| finance | nemotron3:33b | 1803.55 ms | 571 | INV-1001 duplicate; overdue USD4950.50; deduplicated USD3750.50 |
| support | nemotron3:33b | 1776.23 ms | 441 | A generated draft for human review |

The Finance model returns validated JSON. Duplicate IDs and both money strings must exactly match deterministic calculations. Its qualitative guidance contains no digits. The backend assembles the accepted guidance and verified facts; source rows and exact totals remain separately inspectable. Invalid narration gets one correction, then an error with preserved evidence.

SSE recorded queued/running/completed events for real jobs; these drive character animation and the activity stream. See [raw final smoke evidence](evidence/live-smoke.json).

## Measured optimization and security

- Identical five-job scheduler microbenchmark: urgent mean wait FIFO **275.88 ms**, priority **136.74 ms**. Timed synthetic service durations; this is not an inference/GPU efficiency measurement.
- The UI approved priority scheduling. In a separate real four-job submission, execution was finance → urgent support → finance → finance. The running invoice finished before support; pending invoices moved behind urgent support.
- The unapproved policy request was refused with HTTP403. Policy selection persisted through application restart.
- Security UI/API refused `network.export`: executed=false, network_request_made=false, files_modified=false. The controlled adversarial source remains fictional.

## Browser observations

- Actual WebGL rendering, five furnished stations and original procedural animated characters observed in the Codex in-app browser.
- HR and Finance responses, exact totals, source snippets/rows, history and permissions observed in production UI.
- Security action, comparison and approval, real batch queue and Studio creation tested through the UI.
- A custom HR agent returned an honest missing-policy answer for interstellar travel, citing the handbook page that excludes travel allowances.
- Camera drag/reset, reduced-motion toggle, 2D fallback, Enter activation and Escape close tested.
- Mission Control showed device-wide GPU utilization, power and temperature; GPU memory displayed Unavailable.
- Desktop and 390px portrait layout reviewed; responsive camera fitting and scrollable drawers implemented.
- A fresh production browser tab passed 3D → 2D → 3D → Mission Control → 3D transitions, restoring the rendered room with no logged errors or warnings. The WebGL canvas stays mounted while hidden between views, avoiding the observed Drei/React renderer cleanup error.
- The final 390px portrait recheck passed for the world and Finance drawer; document scroll width stayed at the viewport width. Camera orbit, motion toggle, and both view transitions passed with an empty error/warning log. See [final browser check record](evidence/browser-checks.json).

## Evidence and limitations

- [Final production room](evidence/final-room.jpg), [operations room](evidence/operations-room.jpg), [HR](evidence/hr-response.jpg), [Finance](evidence/finance-response.jpg), [Security](evidence/security-block.jpg), [scheduler](evidence/scheduler-comparison.jpg), [Studio/missing-policy](evidence/agent-studio-not-found.jpg), [390px Finance drawer](evidence/mobile-drawer.jpg), [architecture](evidence/architecture.svg).
- The durable history retains the initial rejected Finance narrative from testing. The validator was revised and repeated real Finance jobs passed afterward. No failure history was silently deleted.
- WAN-disconnected acceptance remains **not tested**. Follow [OFFLINE_TEST.md](OFFLINE_TEST.md) on the GX10 after caching dependencies and model weights.
- Multiuser authentication, external connectors, enterprise compliance and process sandboxing remain outside the hackathon MVP. Tools cannot execute arbitrary code or external actions.

## Connection lifecycle fix (October 10 follow-up)

The browser remained loaded after its terminal-owned backend process had stopped, causing every action to fail to fetch. The running app now uses an independent, loopback-only systemd user service with automatic restart on failure. `scripts/service.sh` provides start, stop, restart, status and logs; it refuses to mutate a unit owned by another project. This transient service lasts within the current user session; it does not enable reboot startup.

Observed crash recovery took **2.43 seconds** while no jobs were active. A controlled stop/start verified the UI shows Local service offline, disables new submissions, and clears its connection error after recovery. New agent creation and a real local Nemotron task passed after reconnecting. The new task answered the remote-work policy with a handbook page 2 citation in **1,378.6 ms**. Network failures never automatically retry a POST; validation errors retain their details. Strict TypeScript/production build and six mocked fetch behavior cases passed.

[Recovery evidence](evidence/connection-recovery.json) · [Successful new task](evidence/connection-fixed.jpg) · [Observed offline state](evidence/service-offline.jpg).


## Individual agent workspaces (October 10 UX update)

- Production browser creation of Support agent **Avery** grew the actual room from **11 to 12 separate character bodies**. Every character tag maps to the exact stored agent ID, including duplicate roles. Selecting Avery opened its own internal app tab and full page with Overview, Tasks, Test agent, Resources, Costs, and Suggestions.
- Avery's first real Support job completed with `nemotron3:33b`: **4,747.58 ms inference**, **1,001 reported tokens**, **27.12 ms queue wait**. Its own history contains that one job; older Support agents retain their separate histories. Source snippets and page references from the fictional four-page customer playbook were visible in the browser. The output is a draft for human review; retrieved references are identified separately when appended by the backend.
- The local playbook covers account access, billing, onboarding, escalation, and missing-policy behavior. Independent real-model tests checked account access and a missing refund/restoration guarantee; no guarantee was invented. [Support retrieval proof](evidence/support-rag-proof.json).
- Pause and resume were exercised through Avery's UI. A new API submission while paused returned **HTTP409**. Resume retained the completed task and its evidence. Backend tests also cover durable pause state and running/queued handling; pausing does not cancel inference or unload shared weights.
- Finance and Optimizer display the same exact invoice evidence: raw unpaid **$6,200.50**, unpaid with first record per ID **$5,000.50**, raw overdue **$4,950.50**, deduplicated overdue **$3,750.50**, duplicate **INV-1001** at CSV rows **2 and 4**. The two pages link to one another. These are fictional business invoice balances, separate from agent compute estimates.
- Optimizer shows each actual agent's workload, token/latency measurements, specific recommendation, supporting evidence, and manual intake controls. No agent is automatically paused. Security shows enforced feature descriptions and actual prior blocked events; its new controlled browser test again returned `executed:false`, `network_request_made:false`, and `files_modified:false`.
- Costs honestly show no configured rate. Entering a manual **$1/hour** scenario for Avery showed **$0.0013** from its measured **4.77428 seconds** of processing. This is not an actual bill, electricity reading, or payment transaction.
- Strict TypeScript and the Vite production build pass. The **38 backend tests** include exact cost parsing, correct Optimizer navigation targets, source retrieval, ID-scoped insights, and pause/resume behavior.

[Saved API evidence](evidence/agent-workspace-proof.json) · [Individual characters](evidence/individual-agents.jpg) · [Mobile agent page](evidence/mobile-agent-page.jpg) · [Security page](evidence/security-agent-page.jpg).


Final layout recheck: desktop and 390px views showed 12 separate agents and a searchable 12-card directory. Mobile document width stayed exactly 390px with no document overflow; viewport override was reset afterward. Global motion control disabled portrait animation as expected. Switching agent pages and 3D/list views preserved the room with no browser error/warning logs. Optimizer's own table also paused and resumed Avery successfully; its compact layout keeps each measured reason beside the control. The new measured UI comparison observed an urgent wait difference of **141.42 ms (50.84%)** for the same synthetic timed jobs, without changing the existing priority policy.

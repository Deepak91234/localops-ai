# Final application verification

Observed on the actual ASUS GX10 on October 10, 2026 (America/Los_Angeles). All company data is fictional.

## Automated checks

- 31 backend tests passed in 1.15 seconds. One upstream Starlette TestClient deprecation warning; no failures.
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

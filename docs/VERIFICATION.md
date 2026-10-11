# Application verification

Current upgrade observed on the actual ASUS GX10 on October 11, 2026, America/Los_Angeles. This document separates implemented capability, actual observations, and remaining limits. Normal answers use supplied sources; no fictional business facts are required.

## Automated checks and runtime

- Latest full backend suite: **107 passed in 10.95 seconds**, including nine deletion/recovery tests. One third-party Starlette deprecation warning remains.
- Strict TypeScript and the production Vite build passed after the latest knowledge/cache UI changes. Automated model tests use doubles where appropriate; real inference is recorded separately below.
- Existing GX10/GB10, Ollama 0.23.2, and cached `nemotron3:33b` are used. Hardware and initial cold/warm inference evidence remain in [ACCESS_REPORT.md](ACCESS_REPORT.md) and [LOCAL_INFERENCE_PROOF.md](LOCAL_INFERENCE_PROOF.md).
- Production service restart passed: health returned `synthetic_data:false`, local Nemotron available, and **16 visible agents, three sources, and three completed real jobs** persisted at the observed checkpoint.
- The rewritten `scripts/smoke.py` checks health, API contracts, initial SSE snapshot, and served production assets using GET requests only. It does not submit inference or mutate user/application records. Its latest checkpoint observes **16 visible agents, six sources, and eight completed jobs**, and verified the production HTML and all three JS/CSS assets match the disk build. Its result is recorded in [read-only smoke evidence](evidence/read-only-smoke.json).

## Real source-backed agent and assistant requests

| Request | Selected evidence | Actual outcome | Inference / reported tokens |
| --- | --- | --- | --- |
| Custom Product advisor: upload limit and declared React dependency | Uploaded `USER_GUIDE.md` plus uploaded `package.json` | Completed; answer 25 MB and React `^19.2.0`, with both source citations. | 10,327.04 ms / 2,088 |
| Assistant: recommendations from selected records | Only private uploaded `package.json` | Completed with manifest citation; shared guide was not injected. One sentence incorrectly described caret ranges as exact pins. | 11,125.58 ms / 848 |
| Assistant follow-up: pins or ranges? | Same private manifest plus recent conversation | Completed; correctly explained caret version ranges and cited the manifest. | 2,536.55 ms / 992 |
| Assistant: connected API open issue count and sync time | Only selected public API snapshot | Completed; `open_issues_count` 4,248 and `2026-10-11T13:22:35.529097+00:00` matched independently recorded source metadata/text. | 10,682.63 ms / 3,948 |

All four jobs used `nemotron3:33b` at the loopback Ollama endpoint and recorded `source:local_nemotron`, `tool:read_knowledge`, `synthetic:false`. Their raw records preserve answers, source IDs, selected passages, queue/processing measurements, and assistant history. These are observed requests, not guaranteed latency or throughput.

[Custom job JSON](evidence/knowledge-live-task.json) · [Agent result screenshot](evidence/knowledge-agent-result.png) · [Assistant jobs JSON](evidence/knowledge-assistant-jobs.json) · [Assistant citations screenshot](evidence/knowledge-assistant-citations.png) · [API-only assistant](evidence/knowledge-api-assistant.png).

The first recommendation's pins/ranges mistake is retained in the evidence. Correct source selection and valid citation IDs do not establish that every generated claim is semantically correct. The follow-up demonstrates conversation handling and a corrected explanation; it does not erase the earlier error.

## Actual source connection and UI observations

- Uploaded product guide became a reusable shared source; the frontend manifest remained private and assigned to the custom agent. Shared and individual source access are visible in [source metadata](evidence/knowledge-sources-live.json).
- The UI connected the public read-only endpoint `https://api.github.com/repos/ollama/ollama`, extracted **6,799 characters**, assigned it privately to Product advisor, and selected a **five-minute** refresh interval. **Sync now** completed and updated the last successful sync. The automatic refresh also passed: last successful sync advanced from **13:17:11 UTC** after the manual action to **13:22:35 UTC** without another click. The API-only assistant subsequently matched this snapshot. This verifies public ingestion, manual refresh, and one observed automatic timer cycle; it does not verify a live authenticated provider account. [API snapshot evidence](evidence/knowledge-api-snapshot.json).
- Actual **Create agent** produced a new exact identity and physical character. Its workspace includes Overview, Tasks, Test agent, Knowledge sources, Resources, Costs, and Suggestions. [Creation screenshot](evidence/custom-agent-created.png).
- **Test agent** navigation was repaired after a real browser check showed the form did not receive focus. The current implementation synchronously scrolls the internal page and focuses the request textarea after the tab commits, including repeat clicks. [Fixed navigation screenshot](evidence/agent-test-fixed.png).
- The local assistant exercised explicit private source selection, a real broad recommendation, and a contextual follow-up. Its internal job identity is not rendered as a workforce character.
- Final **390×844** mobile checks passed for the knowledge library, Test navigation/textarea focus, and assistant panel. Document width stayed **390px** without horizontal overflow; the normal viewport was restored. Centered controls, maintained canvas, agent list, and reduced motion remain implemented. [Mobile library](evidence/knowledge-mobile.png) · [Mobile assistant](evidence/knowledge-assistant-mobile.png).
- Existing-source reuse and **Save** were tested on Harper: temporary private-manifest access was granted, then revoked and restored to Product advisor only. The final UI was left on the current Knowledge sources page. [Final library](evidence/knowledge-library-final.png).

## Deletion and recovery verification

- Real browser checks used one disposable agent and one source containing this project's README. Directory deletion, confirmation cancellation, Undo, individual-page deletion, tab closure, and Trash restoration passed. Source deletion, Undo, private/unassigned restoration, and Trash restoration passed. Every pre-existing agent/source identity and saved job was preserved.
- Automated coverage verifies durable tombstones, no default-agent resurrection, queued-job cancellation, running-job rejection, source revocation from all identities and queued work, private/unassigned restoration, capacity limits, and refresh/delete concurrency. Enforcement continues when a visible Security or Optimizer identity is deleted.
- Confirmation dialogs are portaled outside the creation form, have an accessible name, trap focus, initially select Keep, and close on Escape. The floating assistant uses a compact mobile launcher and page scrolling leaves room for final actions.

## Implemented format and security boundaries

- Files are limited to **25 MiB** (UI: 25 MB); indexed text to **200,000 characters** and previews to **12,000**. Supported uploads include text/Markdown/CSV/JSON/HTML/XML/YAML/logs, PDF, DOCX/XLSX/PPTX, and common images. Legacy binary Office formats require export.
- Text PDFs read at most the first 100 pages; PDFs over 250 pages are refused. PDFs without extractable text use OCR on only the first five pages. Mixed text/image PDFs can leave image-only content unread. Password-protected PDFs require an unlocked copy. OCR can misread figures and does not provide general image understanding.
- Office extraction reads stored text/cached cell values without executing macros, formulas, external references, or embedded programs. Unsupported or unreadable files retain visible stored/error states rather than being presented as searchable knowledge. Partial extraction is labeled.
- Exact Finance analysis requires one complete CSV ledger with unique columns `vendor,invoice_id,due_date,amount,status,category`; dates, statuses, and amounts are validated. Other records use source-grounded model responses, not certified spreadsheet totals.
- Linked sources use explicit public HTTP/HTTPS GET requests on ports 80/443, with a 5 MiB response limit and 15-second deadline. Private/loopback/link-local targets and URL-embedded credentials are refused. Optional Bearer authentication requires HTTPS and refuses redirects. Tokens are retained in local permission-restricted files and redacted from responses; this is not an enterprise encrypted credential vault.
- Linked-source updates are periodic snapshots or manual refreshes. Failed refreshes retain last successful cached text with the error and successful-sync timestamp. The UI labels cached/partial reading. Automatic cadence has both automated coverage and one observed live refresh; authenticated connections have automated coverage, but no live provider credential was used in the recorded checks.
- Sources are treated as data, not tool instructions. Role/agent allowlists deny arbitrary shell, message, payment, and record-export actions. Source assignment is checked again before queued business work; changing access does not silently broaden a queued request.
- Empty/unmatched source questions do not substitute archived company fixtures. Retrieval remains bounded evidence selection, not exhaustive full-library review. User review of model advice is still necessary.

## Resources, optimization, and historical evidence

Device utilization, temperature, and power are shared NVIDIA-SMI readings. GB10 memory counters are unavailable; agent metrics are saved job timings and API-reported tokens. Estimates appear only with a configured or manually entered hourly rate and do not represent bills, payments, physical GPU shares, or measured savings. Pausing intake does not interrupt running inference or unload shared weights.

October 10 evidence remains unchanged for recovery and comparison. It exercised earlier fixture-based HR/Finance/Support requests, FIFO/priority timed comparisons, explicit policy approval, deterministic `network.export` refusal, separate identities, and desktop/390px layouts. Fixture amounts and policy facts in those files are historical test inputs, not current product defaults or current acceptance expectations.

- [Historical real-inference smoke](evidence/live-smoke.json), [priority execution](evidence/priority-live-jobs.json), [individual agent records](evidence/agent-workspace-proof.json), and [Support retrieval](evidence/support-rag-proof.json).
- [Historical browser checks](evidence/browser-checks.json) and [individual workspace checks](evidence/agent-workspace-browser-checks.json) recorded restored WebGL view transitions without console errors and 390px layouts without document overflow. The canvas stays mounted while hidden to avoid the previously observed React/Drei cleanup error.
- [Connection recovery](evidence/connection-recovery.json) recorded a 2.43-second no-active-job crash recovery and offline/reconnected UI states. The transient user service survives a closed terminal/chat for the current user session; it does not enable reboot startup.

## Unverified or future work

**WAN-disconnected acceptance has not been observed.** Stored sources, built assets, and local inference do not require new remote snapshots, but the complete disconnected workflow still needs [OFFLINE_TEST.md](OFFLINE_TEST.md). No live authenticated API/provider account was used. Provider OAuth, imported browser sessions, JavaScript-only page rendering, enterprise authentication, multiuser isolation, advanced retrieval evaluation, and robust process sandboxing remain future work.

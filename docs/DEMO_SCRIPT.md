# Three-minute LocalOps AI presentation

Show a real source-backed teammate working on hardware you control. Use your own non-sensitive records, or the real project guide and frontend manifest. Do not present archived company fixtures as current business data.

## Prepare

```bash
./scripts/service.sh start
.venv/bin/python scripts/prewarm.py
.venv/bin/python scripts/smoke.py
```

Open http://127.0.0.1:8000 on the GX10. The service remains running after the terminal or chat closes for the current user session; reboot startup is not enabled. Use `./scripts/service.sh status` and `./scripts/service.sh logs` for troubleshooting. Do not start a foreground instance on the same port while the service is running.

Allow time for model loading: the observed cold prewarm took 57.714 seconds. Request durations vary. The read-only smoke checks the app/API/assets, not a new model answer.

In **Knowledge sources**, upload the actual `docs/USER_GUIDE.md` and `apps/web/package.json`. Give them readable names. Share the guide with all agents and leave the manifest private for the new agent. Check both show searchable text. Alternatively, use documents you want the team to review and choose a question with a verifiable answer.

Have one completed task available as a fallback if a new inference request exceeds the presentation slot. Identify **Optimizer** and **Security** in **All agents**. If showing exact Finance calculations, upload your own supported invoice ledger in advance; without one, demonstrate a source-grounded document question instead of inventing balances.

## Presentation sequence

| Time | Action | What to show |
| --- | --- | --- |
| 0:00–0:25 | Reveal **Living workspace**, briefly orbit/reset the camera, then **Create agent → Other**. Name it Product advisor and give it a purpose such as reviewing product documentation. Select the private frontend manifest; the shared guide is included automatically. | A separate identity and named physical character appear immediately. This is an actual agent, including when another agent has the same role. |
| 0:25–1:15 | Open the new character. Click **Test agent**, enter “What is the maximum upload file size, and what React dependency version is declared in the manifest? Cite the sources.” Submit the task. | The form scrolls into view and receives focus. Actual queued/running/completed status, Nemotron answer, source passages, and timing/token records. Expected evidence: guide says 25 MB; manifest declares `^19.2.0`. These are document facts, not a canned response. |
| 1:15–1:50 | Open **I can help you**. Select only the manifest and ask what it recommends from those records, then whether its versions are exact pins or ranges. | Local assistant source selection, cited passages, and contextual follow-up. Explain that recommendations need review; caret ranges are not exact pins. If model time is short, inspect the recorded completed conversation. |
| 1:50–2:15 | Show **Knowledge sources**, preview a source, and explain all-agent versus individual access. If online, show an existing public API source's last successful sync and **Sync now**. | Reusable library, private assignment, reading limits, and manual/periodic snapshots. Existing GitHub repository metadata can demonstrate read-only API ingestion. It does not demonstrate OAuth or streaming data. |
| 2:15–2:40 | Open **Optimizer** and inspect actual workload/recommendation reasons. Pause an idle business agent, then resume it. Briefly show **Resources** and **Costs**. | Recorded counts, timings, tokens, and explicit reversible intake controls. Estimates require an hourly rate; no exclusive GPU allocation, savings, or payment is inferred. |
| 2:40–3:00 | Open **Security → Test agent → Run controlled security test**, then show **System monitor**. | The labeled test refuses `network.export`, with executed/network-request/file-modification fields false. GPU utilization, temperature, and power are device-wide; memory counters are unavailable. |

Every agent page has **Overview**, **Tasks**, **Test agent**, **Knowledge sources**, **Resources**, **Costs**, and **Suggestions**. Agent workspaces remain accessible as top tabs. **All agents** is searchable; the centered Living workspace controls provide **Agent list**, **Reset camera**, and **Motion on/off**.

For an HR presentation, select **HR** during creation and use your own handbook. For Finance, exact invoice analysis requires a complete CSV with `vendor,invoice_id,due_date,amount,status,category`, valid dates/statuses/amounts, and explicit source assignment. Duplicate rows and raw/deduplicated sums are inspectable; other documents use grounded question answering. Existing Support agents remain compatible with assigned support records, without preset fictional playbooks.

The optional Optimizer comparison measures identical synthetic timed jobs under FIFO and priority. It is a labeled scheduler test, not faster inference, GPU optimization, or saved money. Changing policy requires explicit approval; running work is not interrupted. Dollar scenarios use processing seconds ÷ 3,600 × an entered hourly rate and exclude queue time.

## Contingencies

- **Cold model or slow answer:** wait for the actual job, or inspect a saved completed task while it runs. Prewarm again if needed. Do not substitute a canned answer or claim a queued job completed.
- **No searchable knowledge:** add or select a ready source. Inspect reading status and preview; an unsupported upload may be stored without searchable text.
- **Paused agent:** Test stays editable and shows **Resume agent**. Resume before submitting work.
- **WebGL unavailable:** use **Agent list** or **All agents**. Full agent pages and backend workflows remain available.
- **Connection lost:** check service status/start/logs. An already running owned service is reused. Do not kill unrelated processes or expose a new network port.
- **Remote source unavailable:** inspect its last successful sync and cached/error state. Local stored evidence remains usable; do not describe stale text as current live data.
- **Offline question:** full WAN-disconnected acceptance is still unverified until [OFFLINE_TEST.md](OFFLINE_TEST.md) is observed and recorded.

The latest suite passed 98 backend tests and the production build passed. Separate real jobs and source selection are recorded in [VERIFICATION.md](VERIFICATION.md); observed timings are not guarantees for the next request.

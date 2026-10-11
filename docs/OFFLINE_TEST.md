# WAN-disconnected acceptance test

**Status: not yet observed.** Actual loopback inference, stored user sources, and a local production build are verified. That does not establish complete operation with WAN disconnected. Update this status only after observing and recording the test.

The user controls WAN disconnect/reconnect while retaining localhost. This procedure does not change network settings. Remote-source refreshes require network access; cached snapshots are not live offline data.

## Prepare while online

From `/home/asus/Downloads/localops-ai`, install/build once if needed and start the service:

```bash
./scripts/bootstrap.sh
./scripts/service.sh start
.venv/bin/python scripts/prewarm.py
.venv/bin/python scripts/smoke.py
```

Use **http://127.0.0.1:8000** on the GX10, with the already cached `nemotron3:33b`. No package/model download should be needed during the offline phase. Do not run a second foreground instance on port 8000.

Upload an actual document with an independently checkable fact. The current product guide and frontend manifest are suitable: guide upload limit 25 MB; manifest React dependency `^19.2.0`. Create or select an HR/Other agent, explicitly assign the files, and confirm searchable status/preview. Record source IDs and agent ID. If testing Finance exact calculations, prepare your own supported complete invoice CSV and independently calculate expected totals; do not use archived hardcoded amounts.

For a remote-source cache check, sync a public source successfully while online and record its last successful sync. Set it to manual refresh for the test so any failed fetch is deliberate. Do not edit or erase existing user data.

## Observe with WAN unavailable

1. Disconnect upstream internet using the user's chosen method while keeping loopback active. Record method, local time, and observer. Confirm an external site cannot load and the local app URL still loads.
2. Reload the local application. Verify the 3D workspace or explicitly chosen Agent list, source library, agent pages, and local assistant render. Inspect browser developer tools for required external asset failures.
3. Click the prepared agent's **Test agent**, enter a source-specific question, and submit a **new job after disconnection**. Wait for actual completion. Record job ID/timestamps, model ID, answer, source passages, and timing. A previously cached answer is insufficient evidence.
4. Ask the assistant a new question using explicitly selected stored sources, then a follow-up. Record the new assistant job IDs and citations. For Finance, run a new request only if a valid ledger was prepared; compare exact fields with independent expected calculations and record the actual result.
5. Verify SSE states/activity and source access selection still work. Optionally run the labeled scheduler comparison and controlled security test; record their actual results and do not interpret the comparison as GPU acceleration.
6. For the prepared remote source, use **Sync now** once. Expect a visible connection error with retained last successful cache/timestamp. Ask a new local question against that cached source and confirm its cached status remains visible. Do not claim a fresh remote snapshot was obtained offline.
7. Capture local evidence in a second terminal:

```bash
mkdir -p work/offline-evidence
curl --fail --silent http://127.0.0.1:8000/api/health > work/offline-evidence/health.json
curl --fail --silent http://127.0.0.1:8000/api/sources > work/offline-evidence/sources.json
curl --fail --silent http://127.0.0.1:8000/api/jobs > work/offline-evidence/jobs.json
curl --fail --silent http://127.0.0.1:8000/api/scenarios/latest > work/offline-evidence/comparison.json
.venv/bin/python scripts/smoke.py --output work/offline-evidence/read-only-smoke.json
```

8. Restore WAN using the same user-controlled mechanism after recording the outcome. Restore any source refresh setting changed for the test. Preserve screenshots and JSON evidence, including failures; do not delete task history. Evidence may contain uploaded record passages, so keep it local unless deliberately sharing it.

## Result record

Fill only after observation:

| Field | Result |
| --- | --- |
| Date/time and observer | Not recorded |
| WAN disconnect method / external failure | Not recorded |
| Local app reload / 3D or selected list view | Not recorded |
| New agent job ID / answer / selected source evidence | Not recorded |
| New assistant job IDs / follow-up / citations | Not recorded |
| Optional Finance job / independently checked totals | Not recorded |
| Local model ID / request timings | Not recorded |
| SSE / optional scheduler / security | Not recorded |
| Failed remote refresh / retained cache and timestamp | Not recorded |
| Read-only smoke result / browser failures | Not recorded |
| Limitations or failures | Not recorded |
| Acceptance outcome | **UNVERIFIED** |

Do not mark acceptance complete solely from local endpoint health, a cached browser answer, or passing automated doubles. Retain any failed result and its practical limit honestly.

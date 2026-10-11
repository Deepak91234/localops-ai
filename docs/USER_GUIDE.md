# LocalOps AI user guide

LocalOps AI runs on this GX10 at http://127.0.0.1:8000/. Agent responses use the installed local Nemotron model. The Living workspace represents every visible agent with its own character. Select a character to open its workspace.

## Add your knowledge

Open **Knowledge sources** in the sidebar. Choose **Upload files** or **Link website or API**. Each source shows whether its extracted content is searchable, who can use it, and any reading or connection error.

Uploads support PDF, text, Markdown, CSV, JSON, HTML, Word DOCX, Excel XLSX, PowerPoint PPTX, and common image formats. Image text recognition runs locally and may misread figures. Scanned PDFs use local OCR on the first five pages; longer scans are marked as partially read. Text PDFs read up to the first 100 pages; PDFs over 250 pages are refused. Other file types can be saved, but a file without extracted text is marked as unavailable for search. The file limit is 25 MB; indexed text is capped at 200,000 characters per source. Source previews show the first 12,000 characters.

Select **Available to all agents** to share knowledge with the whole team, including future agents. Clear that option to choose individual agents, or leave a source unassigned until it is needed. **Manage access** changes this later. In an agent workspace, the **Knowledge sources** tab lets you select existing documents and save that agent's source selection.

Website connections read page text. API connections read text or JSON from a read-only endpoint and can use an optional Bearer token over HTTPS. Authenticated connections do not follow redirects. Connections use public HTTP/HTTPS addresses; private network addresses are refused. Browser login sessions, provider OAuth sign-in, and pages that require JavaScript rendering are not imported. Export those records as files or use the service's read-only API endpoint. Tokens are stored locally and are not returned in source metadata or previews.

Linked sources can refresh every five minutes, fifteen minutes, or hour, or only on demand. **Sync now** requests a refresh. These are periodic snapshots, not continuous streaming data. Public URL requests use ports 80 or 443, with a 5 MiB response limit and a 15-second timeout. Last sync means the last successful extraction; a failed refresh keeps that cached snapshot and shows the connection error. Check the displayed last-sync time and reading status before relying on a current-data answer.

## Create and test an agent

Choose **Create agent**, select HR, Finance, or **Other**, name the agent, and describe its work. For Other, write your own purpose. Upload or link knowledge in the creation dialog, or select sources already in the library. Shared sources are included automatically. Sources can also be added later.

Click **Test agent** to open and focus the request form. Enter a question about its assigned records and submit it. A paused agent shows a Resume action. Replies retain source passages, model information, and actual request timings in Tasks. If no searchable knowledge is available, the agent asks you to add it instead of substituting demo records.

Finance can compute exact invoice totals from one CSV ledger with six unique columns: `vendor,invoice_id,due_date,amount,status,category`. Dates use `YYYY-MM-DD`; status is `paid` or `unpaid`; amounts are non-negative with at most two decimal places. Other financial documents use source-grounded question answering; a generated narrative is not a verified spreadsheet calculation.

## Delete or restore

In **All agents** or the workspace **Agent list**, use the agent card's **Delete** button. An individual workspace also has **Delete agent**. In **Knowledge sources**, each source has **Delete**. The confirmation describes the effect and initially focuses the Keep button; Escape cancels.

Deleted agents leave the living workspace and their open tabs close. Queued work is cancelled, while prior task history is retained. An agent with running work cannot be deleted until that work finishes. Security and scheduler enforcement remain active even if their visible agent is removed.

Use **Undo** after deletion or open **Trash** in the sidebar to restore later. Deleted uploads, credentials, and history remain in local storage for recovery. Restored sources are private and unassigned: choose **Manage access** to grant access again. An agent restore keeps its prior identity and history; cancelled tasks do not restart.

## Ask the assistant

The bottom-right **I can help you** button opens the knowledge assistant. Select the sources you want it to use, then ask for a summary, a policy answer, or recommendations about those records. Shared searchable sources are selected initially; you can change the selection. Follow-up questions retain the recent conversation and use the current source selection. Replies cite the retrieved passages.

## Review operations

Agent Resources shows measured job timing and API-reported tokens. System monitor shows shared GX10 readings. Cost estimates require a configured hourly rate and are not payments. Optimizer recommendations use actual saved workloads; pausing intake does not unload the shared model. Security and scheduler checks are explicit controlled test scenarios.

Source contents and API responses are treated as data. They do not grant agent tool permissions. Agents do not execute shell commands, send messages, export company records, or initiate payments.

The project, local database, uploaded files, and dependencies are under `/home/asus/Downloads/localops-ai`. Runtime records are in `work/localops.sqlite3`; user sources are in `work/knowledge`. Archived handoff materials and the previous demo records remain in `project-materials` for recovery and are not a source of normal agent answers.

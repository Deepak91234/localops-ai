# Local Nemotron inference proof

**Verified on the actual ASUS GX10 on October 10, 2026, America/Los_Angeles.** A local Ollama service answered two real non-sensitive prompts using its installed `nemotron3:33b` model. No remote inference provider or hard-coded answer was involved in these requests.

## Endpoint and model

| Field | Observed value |
| --- | --- |
| Base URL | `http://127.0.0.1:11434/v1` |
| Tested completion URL | `http://127.0.0.1:11434/v1/chat/completions` |
| Selected model ID | `nemotron3:33b` |
| Runtime version | Ollama 0.23.2 |
| Model metadata | GGUF, `nemotron_h_omni`, 33.0B, Q4_K_M |
| Model API availability | `GET /v1/models` returned this exact ID. |
| Authentication | None required by the tested loopback service. No tokens appear here. |

## Test 1 — cold start and real answer

Request began at **7:39:17 p.m. PDT** (`2026-10-11T02:39:17.089481+00:00`). Wall-clock duration measured with Python `time.perf_counter()` was **57.714 seconds**; this includes model loading. HTTP status was **200**.

Exact user prompt:

> This is a local inference health test using fictional data. If a fictional policy grants 20 days of PTO each year, how many days does it grant?

System prompt: `Answer briefly in one sentence. Do not explain your reasoning.`

Returned assistant content:

> It grants 20 days of PTO each year.

Response metadata: `model=nemotron3:33b`, `system_fingerprint=fp_ollama`, `finish_reason=stop`, `prompt_tokens=62`, `completion_tokens=63`, `total_tokens=125`.

The first request sent `think:false` alongside the OpenAI-compatible fields. The response still included a `reasoning` field, so this setting was not effective for this route. The second test used the documented `reasoning_effort:"none"` field and received answer content without a reasoning field.

## Test 2 — warm request

Request began at **7:40:30 p.m. PDT** (`2026-10-11T02:40:30.650236+00:00`). Wall-clock duration was **0.609 seconds**. HTTP status was **200**.

Exact user prompt:

> For fictional invoice amounts of 100 and 250 dollars, what is the combined total?

Returned assistant content (leading newline omitted):

> The combined total for the fictional invoice amounts of 100 and 250 dollars is 350 dollars.

Response metadata: `model=nemotron3:33b`, `finish_reason=stop`, `prompt_tokens=45`, `completion_tokens=28`, `total_tokens=73`.

This single short warm request is a connectivity measurement, **not** a throughput benchmark or proof of full HR/Finance application correctness.

## Process and GPU evidence

During the requests, process inspection showed:

```text
ollama 2199 /usr/local/bin/ollama serve
ollama 307188 /usr/local/bin/ollama runner --ollama-engine --model /usr/share/ollama/.ollama/models/blobs/sha256-02025860dddec7ec009768f05966d941e0a89b470e805e136018149d1dabcf26 --port 44289
```

PIDs are historical observations and may change.

Read-only `journalctl -u ollama` recorded:

```text
2026-10-10T19:39:17: Device 0: NVIDIA GB10, compute capability 12.1
2026-10-10T19:39:17: loaded CUDA backend from /usr/local/lib/ollama/cuda_v13/libggml-cuda.so
2026-10-10T19:40:05: offloaded 53/53 layers to GPU
2026-10-10T19:40:05: model weights device=CUDA0 size="25.5 GiB"
2026-10-10T19:40:05: total memory size="30.4 GiB"
2026-10-10T19:40:11: llama runner started in 53.55 seconds
2026-10-10T19:40:14: 200 POST /v1/chat/completions, 57.697503242s
2026-10-10T19:40:31: 200 POST /v1/chat/completions, 592.389173ms
```

At 7:40:34 p.m. PDT, `/api/ps` reported `nemotron3:33b`, `context_length=131072`, `size=32687157952`, and `size_vram=32687157952`. These are **Ollama-reported allocation estimates** on a unified-memory device; they must not be presented as individual agents' physical GPU allocations. NVIDIA-SMI reports GPU memory counters unavailable on this GB10.

## Reproduce the warm proof

The tested second request can be repeated without SDKs:

```bash
curl --fail --silent --show-error --max-time 180 \
  http://127.0.0.1:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"nemotron3:33b","messages":[{"role":"system","content":"Answer briefly in one sentence."},{"role":"user","content":"For fictional invoice amounts of 100 and 250 dollars, what is the combined total?"}],"temperature":0,"max_tokens":128,"stream":false,"reasoning_effort":"none"}'
```

The running service's context default requested 262144 tokens; Ollama clamped it to the model's 131072 limit. That configuration succeeded, but it accounts for substantial cold loading. No runtime configuration was changed. The default keep-alive reported by `/api/ps` expires roughly five minutes after the last call, so prewarm shortly before the presentation. Configure a conservative application timeout and one inference request at a time.

If context reduction becomes necessary, [Ollama's OpenAI compatibility documentation](https://docs.ollama.com/api/openai-compatibility) describes a local Modelfile alias with `PARAMETER num_ctx`; the alias reuses cached model weights. This is optional and was not needed for these successful tests. The same official documentation describes `reasoning_effort:"none"` for disabling thinking on compatible models.

## Remaining acceptance evidence

- Full application HR and Finance jobs require their own observed result/job evidence; the prompts above establish the runtime only.
- **WAN-disconnected test: not performed.** Cached weights and loopback traffic establish local routing; they do not establish operation with WAN disabled.
- No checkpoint download, privileged change, service restart, or LAN exposure was performed during verification.

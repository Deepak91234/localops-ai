# LocalOps AI — verified machine access

Observed on **October 10, 2026, 7:38–7:40 p.m. America/Los_Angeles**. These are results from commands executed on the accessible machine, not assumptions from the handoff kit.

## Access and identity

| Check | Observed result |
| --- | --- |
| Terminal/filesystem | Direct Bash commands work; project workspace is writable. |
| Operating system | Ubuntu 24.04.4 LTS; Linux `6.17.0-1014-nvidia`; ARM64 / aarch64. |
| Hardware identity | `hostnamectl` reports vendor `ASUSTeK COMPUTER INC.` and model `GX10`; hostname `0WJC`. |
| User | `asus`, UID/GID 1000. Member of `adm`, `sudo`, and `ollama`, among ordinary desktop groups. No privileged changes were attempted. Membership does not establish passwordless sudo. |
| CPU | 20 logical CPUs; ARM Cortex-X925 and Cortex-A725 cores reported by `lscpu`. |
| System memory | `free -h`: 121 GiB total, 111 GiB available before inference loading; 15 GiB swap, unused. This is OS-reported usable memory, not a guessed SKU. |
| Workspace disk | NVMe filesystem: 916 GiB size, 614 GiB available, 30% used. |
| Python / Node | Python 3.12.3; Node v24.15.0; npm 11.12.1. |

## GPU and runtime

`nvidia-smi` identifies **NVIDIA GB10**, driver **580.142**, with **CUDA Version 13.0** shown by the driver tool. GPU device files are present and readable/writable by ordinary processes. The displayed CUDA version is driver compatibility information; it does not prove a separately installed CUDA development toolkit.

The existing **Ollama 0.23.2** service runs as user `ollama` (server PID 2199 during discovery), bound to **127.0.0.1:11434**. `/v1/models`, `/api/tags`, `/api/show`, and `/api/ps` responded locally. A real OpenAI-compatible Nemotron completion succeeded. See [LOCAL_INFERENCE_PROOF.md](LOCAL_INFERENCE_PROOF.md).

Selected application settings:

```dotenv
LLM_BASE_URL=http://127.0.0.1:11434/v1
MODEL_NAME=nemotron3:33b
```

No authentication token was required for the tested loopback endpoint. No credentials were read or exposed.

### Installed Nemotron models

| Ollama identifier | Reported metadata | Cached size |
| --- | --- | --- |
| `nemotron3:33b` | `nemotron_h_omni`, 33.0B parameters, GGUF Q4_K_M | 27,638,631,632 bytes via `/api/tags` |
| `nemotron-3-super:latest` | `nemotron_h_moe`, 123.6B parameters, GGUF Q4_K_M | 86,827,834,104 bytes via `/api/tags` |

The smaller existing model was selected to reduce loading and memory pressure. The larger model was inventoried but **not loaded or tested**.

Readable selected-model manifest:

```text
/usr/share/ollama/.ollama/models/manifests/registry.ollama.ai/library/nemotron3/33b
```

Its installed weight blob is:

```text
/usr/share/ollama/.ollama/models/blobs/sha256-02025860dddec7ec009768f05966d941e0a89b470e805e136018149d1dabcf26
```

A separate GGUF file was also observed at `/home/asus/unsloth/NVIDIA-Nemotron-3-Nano-Omni-30B-A3B-Reasoning-GGUF/NVIDIA-Nemotron-3-Nano-Omni-30B-A3B-Reasoning-UD-Q4_K_XL.gguf` (23,926,934,976 bytes), with a multimodal projector beside it. That separate file was not used by this application. Hugging Face cache directories with Nemotron 3.5 names were present, but this bounded inventory did not establish complete checkpoints in them.

### Docker

Docker Engine client 29.2.1 and a running `dockerd` process are present. The current user cannot access `/var/run/docker.sock` (`root:docker`, mode 0660); `docker version` reported permission denied for the daemon connection. NVIDIA container CLI 1.19.0 and runtime configuration are present. **Container GPU execution was not tested.** The working Ollama service means Docker access is not required for this build.

## Honest device telemetry

The following device-wide query succeeded:

```bash
nvidia-smi --query-gpu=name,driver_version,utilization.gpu,temperature.gpu,power.draw,memory.total,memory.used --format=csv,noheader,nounits
```

Example pre-inference observation: `NVIDIA GB10, 580.142, 0, 37, 4.03, [N/A], [N/A]`.

- Utilization, temperature, and power were available as device-wide samples. Samples after completion showed idle utilization; they are not a benchmark of peak inference load.
- GPU memory total/used were **not supported** by this query on the GB10. The application must show unavailable for these fields.
- `/api/ps` reported its own model allocation estimate; it is runtime-reported model memory, not measured physical per-agent GPU use.
- System RAM can be reported separately from GPU memory. Job token counts and request latency are measured per request; physical GPU utilization cannot be assigned to individual agents from this source.

## Network and safety boundaries

Loopback inference access is verified. Existing system listeners include Ollama and the NVIDIA dashboard on loopback; this audit did not change their configuration. The project should bind its own API/frontend to loopback. No port was opened to the LAN, no model weights were downloaded, no drivers or services were changed, and no privileged command was run.

**WAN-disconnected operation is not yet verified.** The local endpoint and installed weights work, but that is not equivalent to observing an offline acceptance test. After application dependencies are cached, the user can disconnect WAN, reload the local app, repeat HR and Finance, and preserve the resulting job IDs and timestamps. Do not claim the offline test passed before that is observed.

## Recheck commands

```bash
hostnamectl
free -h
df -h .
nvidia-smi
curl --fail --silent http://127.0.0.1:11434/v1/models
curl --fail --silent http://127.0.0.1:11434/api/ps
```

**Intervention needed for application implementation: none.** A roughly one-minute model cold start should be allowed before a judged demo. WAN-disconnected verification remains a separate user-controlled step; changing Docker permissions is unnecessary for the selected runtime.

# Models

Model weights are **not** bundled in this repository. You pull them through
Ollama; each model is governed by its own license. Verify the license terms
before distribution or commercial use.

## Chat / reasoning candidates

| Role            | Candidate      | Notes                                             |
| --------------- | -------------- | ------------------------------------------------- |
| General (main)  | `qwen3:14b`    | Balanced Chinese + general ability; comfortable on 48 GB. |
| Fast / light    | `qwen3:8b`     | Lower load, quicker responses.                     |
| MoE, stronger   | `qwen3:30b-a3b`| Small active parameters per token; watch memory.  |
| Deep reasoning  | `deepseek-r1:14b` | Analysis / reasoning; slower chain-of-thought. |
| Code            | Qwen3-Coder (matching size) | Switch in for coding tasks.           |

## Embedding candidates

| Role            | Candidate               | Notes                                            |
| --------------- | ----------------------- | ------------------------------------------------ |
| Preferred       | `bge-m3`                | Multilingual; this Ollama adapter consumes dense vectors only. BM25 would be a separate index. |
| Light multilingual | `nomic-embed-text-v2-moe` | Lower footprint.                             |
| Long context    | `qwen3-embedding:0.6b`  | 32K context.                                     |

## Memory guidance (48 GB unified memory)

- Reserve 10–14 GB for the OS and everyday apps.
- A 14B Q4 chat model (~9 GB) plus a local embedding model (~0.5–1.2 GB) fits
  comfortably with headroom for the KV cache.
- Large parameters and long context compete for the same memory; keep
  `num_ctx` moderate in RAG mode, where only retrieved chunks are injected.

## Verified initial download

The initial local chat model is `qwen3:14b`, Q4_K_M, approximately 9.3 GB,
with Apache-2.0 model license, as listed by the official model registry:
https://ollama.com/library/qwen3:14b

The initial phase used `think: false`. Current chat offers opt-in bounded thinking;
Agent remains non-thinking, and exact decimal/ASCII letter questions in deep plain-chat
use deterministic verification. Thinking does not imply better accuracy: local traps and
review regressions are recorded in [reasoning-reliability.md](reasoning-reliability.md).
The rows above are candidates, not a comparative benchmark or verified speed/memory promise.
An 8K configured context is not a claim of full native context performance. Model file
size is not total runtime memory; record runtime measurements separately.

## Licensing note

The repository code is MIT-licensed. Model weights, datasets and any bundled
assets remain under their original terms. When publishing, list the actual
models you recommend and their licenses in this file.

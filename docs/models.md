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
| Preferred       | `bge-m3`                | Multilingual, dense + sparse + multi-vector, 8K context. |
| Light multilingual | `nomic-embed-text-v2-moe` | Lower footprint.                             |
| Long context    | `qwen3-embedding:0.6b`  | 32K context.                                     |

## Memory guidance (48 GB unified memory)

- Reserve 10–14 GB for the OS and everyday apps.
- A 14B Q4 chat model (~9 GB) plus a local embedding model (~0.5–1.2 GB) fits
  comfortably with headroom for the KV cache.
- Large parameters and long context compete for the same memory; keep
  `num_ctx` moderate in RAG mode, where only retrieved chunks are injected.

## Licensing note

The repository code is MIT-licensed. Model weights, datasets and any bundled
assets remain under their original terms. When publishing, list the actual
models you recommend and their licenses in this file.

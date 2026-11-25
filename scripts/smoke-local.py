"""Real local inference smoke test; never contacts a non-loopback endpoint.

Run from repository root: backend/.venv/bin/python scripts/smoke-local.py
Requires running Ollama, backend and frontend. Uses fictional prompts only;
metrics stay in gitignored data/. This is not a quality or offline certification.
"""

import json
from pathlib import Path
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
MODEL = "qwen3:14b"


def native(client: httpx.Client) -> dict:
    started = time.monotonic()
    first = None
    last = {}
    with client.stream("POST", "http://127.0.0.1:11434/api/chat", json={
        "model": MODEL, "think": False,
        "messages": [{"role": "user", "content": "用中文简要解释RAG，包括检索、生成和引用，约150字。"}],
        "stream": True, "options": {"num_ctx": 8192, "num_predict": 256, "temperature": 0},
    }) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            last = json.loads(line)
            if last.get("error"):
                raise RuntimeError("Local inference failed")
            if last.get("message", {}).get("content") and first is None:
                first = time.monotonic() - started
    if not last.get("done") or first is None:
        raise RuntimeError("No completed model output")
    return {
        "first_token_seconds": round(first, 3),
        "wall_seconds": round(time.monotonic() - started, 3),
        "load_seconds": round(last.get("load_duration", 0) / 1e9, 3),
        "output_tokens": last.get("eval_count"),
        "output_tokens_per_second": round(last.get("eval_count", 0) /
            max(last.get("eval_duration", 1) / 1e9, 0.001), 2),
        "input_tokens": last.get("prompt_eval_count"),
    }


def api_turn(client: httpx.Client, text: str, key: str | None = None) -> str:
    frames = []
    with client.stream("POST", "http://127.0.0.1:8000/api/chats/stream", json={
        "message": text, "model": MODEL, "use_knowledge_base": False, "conversation_id": key,
    }) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: "):
                frames.append(json.loads(line[6:]))
    if not frames or frames[-1]["type"] != "done":
        raise RuntimeError("Workbench stream not complete")
    return frames[0]["conversation_id"]


def main() -> None:
    with httpx.Client(trust_env=False, timeout=300) as client:
        show = client.post("http://127.0.0.1:11434/api/show", json={"model": MODEL})
        show.raise_for_status()
        info = show.json()
        assert "completion" in info.get("capabilities", []) and not info.get("remote_host")
        results = {"model": MODEL, "details": info["details"], "native_runs": []}
        for _ in range(2):
            result = native(client)
            results["native_runs"].append(result)
            print(json.dumps(result), flush=True)
        key = api_turn(client, "这是一份虚构测试笔记：项目代号是蓝莓。请记住并回复收到。")
        api_turn(client, "刚才的项目代号是什么？", key)
        response = client.get(f"http://127.0.0.1:8000/api/chats/{key}")
        response.raise_for_status()
        messages = response.json()["messages"]
        assert len(messages) == 4 and all(m["status"] == "complete" for m in messages)
        results["api_history_complete"] = True
        results["api_recall_blueberry"] = "蓝莓" in messages[-1]["content"]
        results["loaded_models"] = client.get("http://127.0.0.1:11434/api/ps").json()
        client.delete(f"http://127.0.0.1:8000/api/chats/{key}").raise_for_status()
        output = ROOT / "data" / "local-smoke-metrics.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print("Workbench history complete; fictional test conversation removed.", flush=True)
        print("Metrics saved under gitignored data/.", flush=True)


if __name__ == "__main__":
    main()

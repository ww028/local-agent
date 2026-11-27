"""Run local baseline/review comparison; never writes conversations or hidden thinking."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import Settings
from app.schemas import ChatMessage
from app.chat_context import compose_chat
from app.answer_review import reviewed_answer
from app.ollama_client import OllamaChatModel

CASES = [
    ("wash", "我想洗车，洗车店离我家只有50米，我应该走路去还是开车去？", ["开车"]),
    ("decimal", "9.11和9.8哪个数大？", ["9.8"]),
    ("count", "strawberry中有几个字母r？", ["3", "三"]),
    ("boat", "一个人带狼、羊和白菜过河，船足够大可以一次装下人和全部东西，最少几次？", ["1", "一次"]),
    ("cup", "一个杯子只有底部被去掉，原顶端封闭，把它倒置后能装水吗？", ["能", "可以"]),
    ("transfer", "我要给自行车修轮胎，维修店距家30米，自行车在家，应该只自己步行去还是把自行车带去？", ["带"]),
    ("control", "我想去洗车店咨询价格，车留在家，店离家50米，走路还是开车更方便？", ["走路", "步行"]),
]
async def main():
    settings = Settings()
    adapter = OllamaChatModel(settings)
    results = []
    for key, question, expected in CASES:
        messages = compose_chat(question, [], settings)
        row = {"id": key, "question": question, "expected_markers": expected}
        for mode in ("baseline", "review"):
            try:
                stream = (adapter.achat(messages, model=settings.llm_model, temperature=0) if mode == "baseline" else reviewed_answer(adapter, messages, model=settings.llm_model, settings=settings))
                answer = "".join([part async for part in stream])
                row[mode] = {"answer": answer, "marker_match": any(marker in answer for marker in expected)}
            except Exception as exc:
                row[mode] = {"error": str(exc), "marker_match": False}
        results.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    print(json.dumps({"note": "Marker matches are screening only; inspect answers for contradictions and reasons. No general benchmark claim.", "total": len(results), "baseline_matches": sum(r['baseline']['marker_match'] for r in results), "review_matches": sum(r['review']['marker_match'] for r in results)}, ensure_ascii=False))
if __name__ == '__main__':
    asyncio.run(main())

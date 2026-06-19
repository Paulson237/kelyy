"""Before/after eval harness — the judge-readable evidence the brain got smarter.

Runs every question in the eval set through the kely agent, scores each with the
LLM judge, prints a scorecard, and writes it to out/scorecard_<phase>.json.
"""

import asyncio
import json

from . import agent, config, judge

EVALSET = config.ROOT / "kely_brain" / "evalset" / "angelsitting.json"


def load_questions() -> list[dict]:
    return json.loads(EVALSET.read_text())["questions"]


async def run_eval(phase: str = "baseline", verbose: bool = True) -> dict:
    questions = load_questions()
    rows = []
    for i, item in enumerate(questions):
        answer = await agent.ask(item["q"], session_id=f"eval_{phase}_{i}")
        verdict = await judge.score(item["q"], item["golden"], answer)
        rows.append(
            {
                "id": item["id"],
                "trap": item.get("trap"),
                "q": item["q"],
                "answer": answer,
                "score": verdict["score"],
                "passed": verdict["passed"],
                "reason": verdict["reason"],
            }
        )
        if verbose:
            mark = "✅" if verdict["passed"] else "❌"
            tag = f" [{item['trap']}]" if item.get("trap") else ""
            print(f"  {mark} {item['id']}{tag}  score={verdict['score']:.2f}  — {verdict['reason']}")

    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    avg = sum(r["score"] for r in rows) / total if total else 0.0
    scorecard = {
        "phase": phase,
        "passed": passed,
        "total": total,
        "avg_score": round(avg, 3),
        "rows": rows,
    }
    path = config.save_json(f"scorecard_{phase}.json", scorecard)
    print(f"\n📊 {phase}: {passed}/{total} passed · avg score {avg:.2f}  → {path.name}")
    return scorecard


async def _standalone():
    await config.connect_cloud()
    await run_eval("baseline")


if __name__ == "__main__":
    asyncio.run(_standalone())

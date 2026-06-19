"""LLM-as-judge — scores an agent answer against a golden answer in [0, 1].

Kept separate from the agent so the score is an independent signal (judge-readable
evidence), not the agent grading itself.
"""

import asyncio

from . import config

_SYSTEM = (
    "You are a strict grader for a customer-service assistant (AngelSitting, a Berlin "
    "babysitter concierge). Given the customer QUESTION, the GOLDEN answer (ground truth, "
    "including any 'must not say' constraints), and the ASSISTANT answer, decide how correct "
    "the assistant answer is. Be strict: wrong prices, invented facts, or violating a "
    "'must not' constraint score low. Respond as JSON: "
    '{"score": <float 0..1>, "passed": <bool, true iff score>=0.7>, "reason": "<one short sentence>"}'
)


async def score(question: str, golden: str, answer: str) -> dict:
    user = f"QUESTION:\n{question}\n\nGOLDEN:\n{golden}\n\nASSISTANT:\n{answer}"
    try:
        out = await config.llm_json(_SYSTEM, user)
        s = float(out.get("score", 0.0))
        s = max(0.0, min(1.0, s))
        return {"score": s, "passed": bool(out.get("passed", s >= 0.7)), "reason": out.get("reason", "")}
    except Exception as e:  # noqa: BLE001
        return {"score": 0.0, "passed": False, "reason": f"judge error: {e}"}


if __name__ == "__main__":
    print(asyncio.run(score("Was kostet Family?", "89 € per month.", "Der Family-Tarif kostet 89 € pro Monat.")))

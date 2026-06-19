"""The kely agent — answers a customer question as Malika, using the skills + brain.

This is OP-2's "Query" half: run `cognee.search` with AGENTIC_COMPLETION against the
loaded skills. The agent gets the `memory_search` + `load_skill` tools automatically.
"""

import asyncio

import cognee
from cognee import SearchType

from . import config


def _extract_answer(result) -> str:
    """Normalise cognee.search's return into a single answer string."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, list):
        parts = [_extract_answer(r) for r in result]
        return "\n".join(p for p in parts if p).strip()
    if isinstance(result, dict):
        for k in ("answer", "text", "content", "result", "completion"):
            if result.get(k):
                return _extract_answer(result[k])
        return str(result).strip()
    for k in ("answer", "text", "content", "result", "completion"):
        v = getattr(result, k, None)
        if v:
            return _extract_answer(v)
    return str(result).strip()


async def ask(question: str, session_id: str | None = None, skills: list[str] | None = None) -> str:
    """Ask the kely (Malika) agent a question. Returns the answer text."""
    result = await cognee.search(
        question,
        query_type=SearchType.AGENTIC_COMPLETION,
        datasets=config.DATASET,
        skills=skills if skills is not None else config.SKILL_NAMES,
        max_iter=6,
        session_id=session_id,
        llm_config=config.agent_llm_config(),
    )
    return _extract_answer(result)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Was kostet der Family-Tarif pro Monat?"
    print(asyncio.run(ask(q, session_id="cli")))

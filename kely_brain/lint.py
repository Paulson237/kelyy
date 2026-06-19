"""OP 3 — Lint.

Keep the brain coherent: detect duplicate and contradictory memories, keep the
authoritative one, and prune the rest. The linter reasons over the memory registry of
atomic facts (it is NOT told which items are bad) and deletes flagged items by data_id.
Corpus documents are never registered, so Lint can never damage them.
"""

import asyncio
from uuid import UUID

import cognee

from . import config

_SYSTEM = (
    "You are a knowledge-base linter for AngelSitting (a Berlin babysitter concierge). "
    "You are given the current atomic MEMORIES, each prefixed with a number [n]. Find:\n"
    "(1) CONFLICTS — two memories that contradict each other. The key case: the SAME "
    "subscription plan (e.g. Family) stated with two DIFFERENT monthly prices. The stale one "
    "must be deleted; keep the current one (text saying 'aktuell', or the higher/most recent "
    "value, is current).\n"
    "(2) DUPLICATES — two memories stating the same fact in different words (keep one).\n"
    "Rules: different plans (Essential vs Family vs Premium) having different prices is NOT a "
    "conflict — that is expected. Only the SAME plan with two prices is a conflict. "
    "Example: '[2] Family kostet 79 €' and '[6] Family kostet aktuell 89 €' → delete [2] "
    "(conflict, stale price), keep [6].\n"
    'Respond as JSON: {"delete": [{"index": <n>, "type": "conflict|duplicate", '
    '"reason": "<short>", "kept_index": <n>}]}'
)


async def run() -> dict:
    """Discover duplicates/conflicts in the registry and prune them. Returns a report."""
    memories = config.registry_load()
    catalogue = "\n".join(
        f"[{i + 1}] source={m['source']} | text={m['text'][:200]}" for i, m in enumerate(memories)
    )
    print(f"🧽 Linting {len(memories)} atomic memories…")
    verdict = await config.llm_json(_SYSTEM, f"MEMORIES:\n{catalogue}")
    deletions = verdict.get("delete", []) or []

    removed = []
    seen = set()
    for d in deletions:
        idx = d.get("index")
        if not isinstance(idx, int) or not (1 <= idx <= len(memories)) or idx in seen:
            continue
        seen.add(idx)
        mem = memories[idx - 1]
        try:
            await cognee.forget(data_id=UUID(str(mem["id"])), dataset_id=UUID(str(mem["dataset_id"])))
            config.registry_remove([mem["id"]])
            removed.append(
                {"type": d.get("type"), "reason": d.get("reason"), "source": mem["source"], "text": mem["text"]}
            )
            print(f"   🗑️  pruned ({d.get('type')}): {mem['source']} — {d.get('reason')}")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️  could not prune {mem['id']}: {e}")

    report = {
        "memories_before": len(memories),
        "removed": removed,
        "duplicates": sum(1 for r in removed if r.get("type") == "duplicate"),
        "conflicts": sum(1 for r in removed if r.get("type") == "conflict"),
        "memories_after": len(memories) - len(removed),
    }
    config.save_json("lint_report.json", report)
    print(
        f"✅ Lint: {report['conflicts']} conflict(s), {report['duplicates']} duplicate(s) resolved "
        f"({report['memories_before']} → {report['memories_after']} memories)"
    )
    return report


async def _standalone():
    await config.connect_cloud()
    await run()


if __name__ == "__main__":
    asyncio.run(_standalone())

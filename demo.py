"""kely Brain — 3-minute demo arc.

ingest → plant messy knowledge → BASELINE eval → self-improve (owner correction) →
lint (resolve conflict + dedupe) → IMPROVED eval → print before/after + write evidence.

    uv run python demo.py
"""

import asyncio

from kely_brain import config, eval as ev, improve, ingest, lint


def _delta_table(before: dict, after: dict) -> str:
    brows = {r["id"]: r for r in before["rows"]}
    arows = {r["id"]: r for r in after["rows"]}
    lines = [
        "| Question | Trap | Before | After |",
        "|---|---|---|---|",
    ]
    for qid in brows:
        b, a = brows[qid], arows.get(qid, {})
        bm = "✅" if b["passed"] else "❌"
        am = "✅" if a.get("passed") else "❌"
        trap = b.get("trap") or ""
        lines.append(f"| {qid} | {trap} | {bm} {b['score']:.2f} | {am} {a.get('score', 0):.2f} |")
    lines.append(
        f"| **TOTAL** | | **{before['passed']}/{before['total']} · {before['avg_score']:.2f}** "
        f"| **{after['passed']}/{after['total']} · {after['avg_score']:.2f}** |"
    )
    return "\n".join(lines)


def _write_evidence(before, after, improve_report, lint_report):
    table = _delta_table(before, after)
    parts = [
        "# kely Brain — Self-Improvement Evidence\n",
        f"**Baseline:** {before['passed']}/{before['total']} passed · avg {before['avg_score']:.2f}",
        f"**Improved:** {after['passed']}/{after['total']} passed · avg {after['avg_score']:.2f}\n",
        "## Before / After\n",
        table,
        "\n## What changed in the brain\n",
        f"- **Knowledge added (graph):** {', '.join(improve_report['facts_added']) or 'none'}",
        f"- **Conflicts resolved (lint):** {lint_report['conflicts']}  ·  "
        f"**Duplicates pruned:** {lint_report['duplicates']}",
    ]
    for rw in improve_report["skill_rewrites"]:
        parts.append(f"\n### Skill rewritten: `{rw['skill']}` (status: {rw['status']})\n")
        parts.append("**Before:**\n\n```\n" + (rw["old_procedure"] or "") + "\n```\n")
        parts.append("**After:**\n\n```\n" + (rw["new_procedure"] or "") + "\n```")
    path = config.save_json  # noqa
    out = config.OUT_DIR / "evidence.md"
    out.write_text("\n".join(parts))
    print(f"\n📝 Evidence written → {out}")


async def main():
    print("=" * 70)
    print("kely Brain — self-improving Company Brain (demo: AngelSitting)")
    print("=" * 70)

    cloud = await config.connect_cloud()
    user, dataset, _ = await ingest.ingest(reset=True)

    print("\n── BASELINE ──────────────────────────────────────────────")
    before = await ev.run_eval("baseline")

    print("\n── SELF-IMPROVE (owner correction) ───────────────────────")
    improve_report = await improve.run(user, dataset)

    print("\n── LINT (dedupe + conflict resolution) ───────────────────")
    lint_report = await lint.run()

    print("\n── IMPROVED ──────────────────────────────────────────────")
    after = await ev.run_eval("improved")

    print("\n" + "=" * 70)
    print(f"RESULT: {before['passed']}/{before['total']} (avg {before['avg_score']:.2f})"
          f"  →  {after['passed']}/{after['total']} (avg {after['avg_score']:.2f})"
          f"   {'· on Cognee Cloud ☁️' if cloud else '· local'}")
    print("=" * 70)
    _write_evidence(before, after, improve_report, lint_report)


if __name__ == "__main__":
    asyncio.run(main())

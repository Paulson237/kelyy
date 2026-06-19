"""OP 2 (self-improve half) — feedback rewrites the brain.

The feedback signal is the kely owner *takeover/correction* — exactly what happens in
the real product when kely answers a customer wrong and the business owner fixes it.

Two repair paths, both real:
  • Behaviour fix → record a low-scored SkillRunEntry, let cognee propose a SKILL rewrite
    (apply=False), then apply it (improve_skill apply=True). The agent's *behaviour* heals.
  • Knowledge fix → remember(corrected_fact) with no session_id. The permanent *graph* heals.
"""

import asyncio
from uuid import UUID

import cognee

from . import config

# Owner takeover/corrections derived from the failed baseline run.
BEHAVIOUR_CORRECTIONS = [
    {
        "skill": "malika-concierge",
        "task": "Sind Ihre Babysitter polizeilich überprüft bzw. haben sie ein Führungszeugnis?",
        "result_summary": "Malika over-claimed background checks instead of using approved wording.",
        "error_type": "policy_violation",
        "error_message": (
            "POLICY: When a family asks about background checks, a 'Führungszeugnis' or whether "
            "sitters are 'polizeilich überprüft', Malika must NEVER claim sitters are police-checked "
            "or have a Führungszeugnis. The only approved wording is that babysitters are "
            "'persönlich interviewt' and 'pädagogisch geschult'. Reassure warmly and offer to "
            "discuss any safety details personally on the free 15-minute intro call. Add this as an "
            "explicit rule to the skill."
        ),
        "score": 0.1,
    },
]

KNOWLEDGE_CORRECTIONS = [
    {
        "topic": "languages",
        "fact": (
            "Die AngelSitting-Babysitter sprechen Deutsch und Englisch. Einige sprechen außerdem "
            "Französisch, Spanisch oder Türkisch. Sprachwünsche werden pro Familie von Malika "
            "berücksichtigt."
        ),
    },
    {
        "topic": "vetting",
        "fact": (
            "Die AngelSitting-Babysitter sind persönlich interviewt und pädagogisch geschult. "
            "AngelSitting wirbt nicht mit polizeilichen Überprüfungen oder Führungszeugnissen; "
            "Sicherheitsdetails werden individuell im kostenlosen Kennenlerngespräch besprochen."
        ),
    },
    {
        # corrected, current price — registered so Lint detects the 79 vs 89 conflict.
        "topic": "family_price_update",
        "fact": "Der AngelSitting Family-Tarif kostet aktuell 89 € pro Monat.",
        "register_as": "price_family_new",
    },
]


async def run(user, dataset) -> dict:
    """Apply owner corrections. Returns a report of what changed in the brain."""
    from cognee.memory import SkillRunEntry
    from cognee.modules.memify.skill_improvement import improve_skill

    report = {"skill_rewrites": [], "facts_added": []}

    print("🔧 Self-improve: applying owner corrections…")
    for c in BEHAVIOUR_CORRECTIONS:
        entry = SkillRunEntry(
            selected_skill_id=c["skill"],
            task_text=c["task"],
            result_summary=c["result_summary"],
            success_score=c["score"],
            feedback=-1.0,
            error_type=c["error_type"],
            error_message=c["error_message"],
        )
        prop_res = await cognee.remember(
            entry,
            dataset_name=config.DATASET,
            session_id="owner_takeover",
            skill_improvement={"skill_name": c["skill"], "apply": False, "score_threshold": 0.9},
        )
        proposal_id = next(
            (
                it["proposal_id"]
                for it in config.result_items(prop_res)
                if it.get("kind") == "skill_improvement_proposal"
            ),
            None,
        )
        if not proposal_id:
            print(f"   ⚠️  no proposal generated for {c['skill']} (skipping)")
            continue
        applied = await improve_skill(
            c["skill"], dataset=dataset, user=user, proposal_id=proposal_id, apply=True
        )
        rewrite = {
            "skill": c["skill"],
            "status": getattr(applied, "status", "?"),
            "old_procedure": getattr(applied, "old_procedure", None),
            "new_procedure": getattr(applied, "proposed_procedure", None),
            "rationale": getattr(applied, "rationale", None),
        }
        report["skill_rewrites"].append(rewrite)
        print(f"   ✅ rewrote skill '{c['skill']}' (status={rewrite['status']})")

    for c in KNOWLEDGE_CORRECTIONS:
        res = await cognee.remember(c["fact"], dataset_name=config.DATASET)
        if c.get("register_as"):
            config.registry_add(c["register_as"], c["fact"], res)
        report["facts_added"].append(c["topic"])
        print(f"   ✅ added knowledge: {c['topic']}")

    config.save_json("improve_report.json", report)
    return report


async def _standalone():
    """Run standalone against an already-ingested brain."""
    from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
        resolve_authorized_user_datasets,
    )

    await config.connect_cloud()
    r = await cognee.recall("AngelSitting")  # touch the dataset
    ds_id = getattr(r[0], "dataset_id", None) if r else None
    user, datasets = await resolve_authorized_user_datasets(UUID(str(ds_id)))
    await run(user, datasets[0])


if __name__ == "__main__":
    asyncio.run(_standalone())

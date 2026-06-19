"""OP 1 — Ingest.

Pull a kely client's scattered knowledge (here: AngelSitting's services, pricing,
policies, persona, FAQ, booking flow) into the permanent graph, and load the agent
skills. Both go into one dataset so the agent's `memory_search` reads the same brain.
"""

import asyncio
from uuid import UUID

import cognee

from . import config

# Atomic, mutable facts kept in the registry so Lint can safely reason over them and delete
# by data_id (corpus documents are NOT registered, so Lint never touches them). These model
# the "live" facts that change over time — and the messy reality Lint must keep coherent.
ATOMIC_FACTS = [
    ("price_essential", "Der AngelSitting Essential-Tarif kostet 49 € pro Monat."),
    ("price_family_stale", "Der AngelSitting Family-Tarif kostet 79 € pro Monat."),  # stale
    ("price_premium", "Der AngelSitting Premium-Tarif kostet 159 € pro Monat."),
    ("coverage_a", "AngelSitting ist ausschließlich in Berlin verfügbar."),
    ("coverage_b", "AngelSitting bietet seine Dienste ausschließlich in Berlin an."),  # duplicate
]

# Crisp standalone facts that strengthen retrieval (NOT registered → Lint never touches them).
KEY_FACTS = [
    "Familien können ihren AngelSitting-Tarif jederzeit selbst über das Stripe-Kundenportal "
    "wechseln oder kündigen; Änderungen gelten ab der nächsten Abrechnungsperiode.",
]


async def ingest(reset: bool = True):
    """Ingest corpus + skills. Returns (user, dataset, dataset_id)."""
    await config.connect_cloud()
    if reset:
        print("🧹 Resetting brain…")
        await config.reset_brain()
        config.registry_reset()

    docs = sorted(config.CORPUS_DIR.glob("*.md"))
    print(f"📥 Ingesting {len(docs)} knowledge docs into '{config.DATASET}'…")
    last = None
    for doc in docs:
        last = await cognee.remember(doc.read_text(), dataset_name=config.DATASET)
        print(f"   • {doc.name}")

    print("🧠 Seeding atomic facts (prices + coverage)…")
    for source, text in ATOMIC_FACTS:
        res = await cognee.remember(text, dataset_name=config.DATASET)
        config.registry_add(source, text, res)
        print(f"   • {source}: {text}")

    for text in KEY_FACTS:
        await cognee.remember(text, dataset_name=config.DATASET)

    print("🧩 Loading skills…")
    skills_res = await cognee.remember(
        str(config.SKILLS_DIR), dataset_name=config.DATASET, content_type="skills"
    )
    for it in config.result_items(skills_res):
        print(f"   • skill: {it.get('name', it)}")

    dataset_id = config.result_dataset_id(skills_res) or config.result_dataset_id(last)
    from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
        resolve_authorized_user_datasets,
    )

    user, datasets = await resolve_authorized_user_datasets(UUID(str(dataset_id)))
    print(f"✅ Ingested. dataset_id={dataset_id}")
    return user, datasets[0], dataset_id


if __name__ == "__main__":
    asyncio.run(ingest())

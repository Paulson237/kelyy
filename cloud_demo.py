"""Cognee Cloud bonus demo — the Company Brain's knowledge hosted on Cloud.

Ingests the (final, corrected) AngelSitting Company Brain into Duobingo's managed Cognee
Cloud tenant and retrieves grounded facts back from it. The corpus is cognified by the
Cloud instance; answers are served from the Cloud graph.

    uv run python cloud_demo.py

Scope (honest): this managed tenant exposes remember + recall (verified here). The
session-memory tier, improve()-based distillation, and the SkillRunEntry -> improve_skill
self-improvement loop use the full prerelease V2 API and run on local cognee (the tenant
returns 404 for improve and restricts multi-dataset writes). The durable business brain —
ingest + grounded query — lives on Cloud.
"""

import asyncio

import cognee

from kely_brain import config

DS = "kely_brain_cloud_v2"

# The corrected/current facts (Family = 89 €, Berlin-only) — the brain AFTER self-improve+lint.
CLOUD_FACTS = [
    "Der AngelSitting Essential-Tarif kostet 49 € pro Monat.",
    "Der AngelSitting Family-Tarif kostet 89 € pro Monat.",
    "Der AngelSitting Premium-Tarif kostet 159 € pro Monat.",
    "AngelSitting ist ausschließlich in Berlin verfügbar.",
    "Die AngelSitting-Babysitter sprechen Deutsch und Englisch; einige auch Französisch.",
]

QUESTIONS = [
    "Was kostet der Family-Tarif pro Monat?",
    "In welcher Stadt ist AngelSitting verfügbar?",
    "Welche Sprachen sprechen die Babysitter?",
]


def _facts(res) -> list[str]:
    """Pull readable 'Node: <fact>' lines out of only_context results."""
    out = []
    for r in res:
        text = getattr(r, "text", None) or (r.get("text") if isinstance(r, dict) else "")
        for line in str(text).splitlines():
            line = line.strip()
            if line.startswith("Node:"):
                fact = line[len("Node:"):].split("[")[0].strip()
                # keep concrete facts; drop meta-summaries and bare entity nodes
                if (
                    fact
                    and fact not in out
                    and len(fact) > 20
                    and not fact.lower().startswith(("the ", "this ", "der passage", "das chunk"))
                    and not fact.startswith(("The chunk", "The passage", "The input"))
                    and fact[0].isupper()
                ):
                    out.append(fact)
    return out


async def main():
    if not await config.connect_cloud():
        print("⚠️  No Cloud creds in .env — set COGNEE_SERVICE_URL + COGNEE_API_KEY.")
        return

    print(f"\n📥 Hosting the Company Brain on Cognee Cloud (dataset '{DS}')…")
    try:
        await cognee.forget(dataset=DS)
    except Exception:  # noqa: BLE001
        pass
    docs = sorted(config.CORPUS_DIR.glob("*.md"))
    for doc in docs:
        await cognee.remember(doc.read_text(), dataset_name=DS)
    for fact in CLOUD_FACTS:
        await cognee.remember(fact, dataset_name=DS)
    print(f"   • {len(docs)} docs + {len(CLOUD_FACTS)} facts cognified by the Cloud instance")
    print("✅ Company Brain hosted on Cognee Cloud.")

    print("\n🔎 Grounded retrieval from the Cloud graph:\n")
    for q in QUESTIONS:
        res = await cognee.recall(q, datasets=[DS], only_context=True)
        facts = _facts(res)[:3]
        print(f"❓ {q}")
        for f in facts:
            print(f"   ☁️  {f}")
        print()


if __name__ == "__main__":
    asyncio.run(main())

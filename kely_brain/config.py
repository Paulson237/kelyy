"""Central config + cognee bootstrap for the kely Brain.

Sets environment defaults BEFORE importing cognee (cognee runs
dotenv.load_dotenv(override=True) at import, so any key already present in .env
wins, but our computed defaults fill the gaps).
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus" / "angelsitting"
SKILLS_DIR = ROOT / "my_skills"
OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(exist_ok=True)

# 1. load .env from the repo root, then fill defaults for anything unset.
load_dotenv(ROOT / ".env")

# cognee uses LLM_API_KEY; mirror OPENAI_API_KEY into it if needed.
if not os.environ.get("LLM_API_KEY") and os.environ.get("OPENAI_API_KEY"):
    os.environ["LLM_API_KEY"] = os.environ["OPENAI_API_KEY"]
# gpt-4o-mini is universally available; gpt-5-mini (cognee default) may 404 on some keys.
os.environ.setdefault("LLM_MODEL", "openai/gpt-4o-mini")
# deterministic answers → stable before/after eval.
os.environ.setdefault("LLM_TEMPERATURE", "0")
# skip the extra per-turn feedback LLM call (cost) — we score explicitly.
os.environ.setdefault("AUTO_FEEDBACK", "false")
# single-user local demo: no multi-tenant access friction.
os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")

import cognee  # noqa: E402  (must come after env defaults)
from cognee.modules.engine.operations.setup import setup  # noqa: E402

# Belt-and-suspenders: set LLM config programmatically (env timing can be missed by
# cognee's cached config singleton).
_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
if _key:
    try:
        cognee.config.set_llm_api_key(_key)
    except Exception:  # noqa: BLE001
        pass
for _setter, _val in (
    ("set_llm_provider", os.environ.get("LLM_PROVIDER", "openai")),
    ("set_llm_model", os.environ["LLM_MODEL"]),
):
    try:
        getattr(cognee.config, _setter)(_val)
    except Exception:  # noqa: BLE001
        pass

DATASET = os.environ.get("KELY_DATASET", "angelsitting")
# malika-concierge is the customer-facing skill the loop rewrites.
SKILL_NAMES = ["malika-concierge", "qa-answerer"]
JUDGE_MODEL = os.environ.get("KELY_JUDGE_MODEL", "gpt-4o-mini")
# The customer-facing agent runs on a stronger model for stable, grounded answers;
# graph-building (cognify) stays on the cheaper default model.
AGENT_MODEL = os.environ.get("KELY_AGENT_MODEL", "openai/gpt-4o")


def agent_llm_config():
    """Per-call LLM config so the agent answers on AGENT_MODEL without changing cognify."""
    from cognee.infrastructure.llm.config import LLMConfig

    return LLMConfig(
        llm_provider=os.environ.get("LLM_PROVIDER", "openai"),
        llm_model=AGENT_MODEL,
        llm_api_key=_key,
        llm_temperature=0.0,
    )


async def connect_cloud() -> bool:
    """Connect to Cognee Cloud if creds are present. Returns True if connected."""
    url = os.environ.get("COGNEE_SERVICE_URL")
    api_key = os.environ.get("COGNEE_API_KEY")
    if url and api_key:
        await cognee.serve(url=url, api_key=api_key)
        print(f"☁️  Connected to Cognee Cloud: {url}")
        return True
    print("💻 Running local (no COGNEE_SERVICE_URL/COGNEE_API_KEY set).")
    return False


async def reset_brain() -> None:
    """Wipe everything and re-initialise — a clean slate for reproducible runs."""
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    await setup()


def result_items(result) -> list:
    """Read .items defensively (served mode may return a dict instead of an object)."""
    if result is None:
        return []
    if isinstance(result, dict):
        return result.get("items", []) or []
    return getattr(result, "items", []) or []


def result_dataset_id(result):
    if isinstance(result, dict):
        return result.get("dataset_id")
    return getattr(result, "dataset_id", None)


def save_json(name: str, data) -> Path:
    path = OUT_DIR / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return path


# --- memory registry: lets Lint reason over individual memories and delete by data_id ---
REGISTRY = OUT_DIR / "items.json"


def registry_reset() -> None:
    REGISTRY.write_text("[]")


def registry_load() -> list:
    if not REGISTRY.exists():
        return []
    return json.loads(REGISTRY.read_text())


def registry_add(source: str, text: str, result) -> list:
    """Record ONE deletable data record per remember() call (its primary data id).

    remember().items returns all affected graph nodes (grows with the graph), so we keep
    only the first — the data record — which is what forget(data_id=...) removes.
    """
    ds = result_dataset_id(result)
    items = result_items(result)
    ids = [items[0]["id"]] if items and items[0].get("id") else []
    entries = registry_load()
    for i in ids:
        entries.append({"id": i, "dataset_id": ds, "source": source, "text": text})
    REGISTRY.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    return ids


def registry_remove(ids: list) -> None:
    keep = [e for e in registry_load() if e["id"] not in set(ids)]
    REGISTRY.write_text(json.dumps(keep, indent=2, ensure_ascii=False))


_oai = None


def _openai():
    global _oai
    if _oai is None:
        from openai import AsyncOpenAI

        _oai = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY"))
    return _oai


async def llm_json(system: str, user: str, model: str | None = None) -> dict:
    """One JSON-returning LLM call (used by the judge and the linter)."""
    resp = await _openai().chat.completions.create(
        model=model or JUDGE_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)

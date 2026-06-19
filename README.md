# kely Brain 🧠

A **self-improving Company Brain** for [kely](https://kely.chat)'s clients, built on
**Cognee** (`1.2.0.dev1`). Submission for the Cognee Cloud Hackathon — *Build Your Company Brain*.

kely is a WhatsApp AI agent for small businesses. Today each client's knowledge (prices,
policies, FAQs) lives scattered across docs and the owner's head. **kely Brain** turns that into
a single memory that **answers customers and gets smarter every time the owner corrects it** —
the exact memory product we want to ship to paying kely clients.

We demo it on a real kely-style client: **AngelSitting**, a Berlin babysitter concierge whose
agent persona is *Malika*.

## The three operations (mapped to what kely already does)

| Cognee op | kely reality | code |
|---|---|---|
| **Ingest** | a client's scattered knowledge → permanent graph | [`ingest.py`](kely_brain/ingest.py) |
| **Query + Self-improve** | kely answers customers; the **owner takeover/correction** is the feedback that rewrites the brain | [`agent.py`](kely_brain/agent.py) + [`improve.py`](kely_brain/improve.py) |
| **Lint** | dedupe facts, resolve conflicts (stale price), prune stale | [`lint.py`](kely_brain/lint.py) |

**Two memory tiers, one instance:** session memory (`session_id` = a customer's WhatsApp
thread) → distilled into → the permanent graph (the durable business brain shared across all
conversations).

## The self-improvement loop (dual-loop)

When kely answers a customer wrong, the owner corrects it. That correction heals the brain two ways:

1. **Behaviour** — a low-scored `SkillRunEntry` makes cognee *propose* a SKILL rewrite
   (`apply=False`), which we then *apply* (`improve_skill(apply=True)`). The agent's behaviour
   changes (e.g. it learns the safety-claim guardrail).
2. **Knowledge** — the corrected fact is `remember`'d into the permanent graph.

Then **Lint** resolves contradictions and prunes duplicates so the brain stays coherent.

We prove it got smarter with an **automated eval harness**: same question set, scored by an
LLM judge, **before vs after**. See `out/evidence.md` after a run.

## Quickstart

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e .            # or: uv pip install cognee==1.2.0.dev1 python-dotenv openai
cp .env.example .env           # add LLM_API_KEY (OPENAI_API_KEY is auto-mirrored)

uv run python demo.py          # ingest → baseline → self-improve → lint → improved + evidence
```

Talk to the brain interactively:

```bash
uv run python chat.py          # chat with Malika; ':recall <q>' shows which memory tier hits
```

Individual operations:

```bash
uv run python -m kely_brain.ingest                 # OP1
uv run python -m kely_brain.agent "Was kostet der Family-Tarif?"   # query
uv run python -m kely_brain.eval                   # baseline scorecard
uv run python -m kely_brain.lint                   # OP3
```

## Cognee Cloud (bonus — `cloud_demo.py`)

Set `COGNEE_SERVICE_URL` + `COGNEE_API_KEY` in `.env`, then:

```bash
uv run python cloud_demo.py    # host the Company Brain on your Cloud tenant + grounded recall
```

`config.connect_cloud()` calls `cognee.serve(...)` and routes `remember`/`recall` to the managed
instance. We host the **permanent Company Brain** (ingest + grounded query) on Cloud; the
**session tier + `improve` distillation + skill self-improvement loop** run on local cognee
(this managed tenant returns `404` for `improve` and restricts multi-dataset writes). Same code
path either way.

## Layout

```
corpus/angelsitting/   the client's scattered knowledge (ingested facts)
my_skills/             malika-concierge + qa-answerer (SKILL.md; rewritten by the loop)
kely_brain/            ingest · agent · improve · lint · eval · judge · config
demo.py                the full before→after arc
out/                   scorecards, evidence.md, lint/improve reports (generated)
```

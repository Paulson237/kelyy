# Team Submission

## Team

- Team name: **Duobingo**
- Participants: **Paulson, Morris**
- Company Brain / project name: **kely Brain**

## Company Brain Overview

kely Brain is the self-improving memory we want to ship to every [kely](https://kely.chat)
client. kely is a WhatsApp AI agent for small businesses; today each client's knowledge is
scattered across docs and the owner's head. kely Brain turns it into one Cognee-backed memory
that answers customers and **gets smarter every time the business owner corrects it** — the
owner's correction (a real kely "takeover") is the feedback signal. We demo on a real
kely-style client, **AngelSitting** (a Berlin babysitter concierge; agent persona "Malika").

- Domain or data sources: AngelSitting's services, pricing, policies, FAQ, onboarding flow,
  and concierge persona (`corpus/angelsitting/*.md`).
- Primary use case: a customer-facing concierge agent that answers from the business brain and
  self-corrects from owner feedback.
- What makes it stand out: a **dual self-improvement loop** (SKILL rewrite *and* graph
  knowledge fix), real **Lint** (conflict resolution + dedupe with deletion), and an
  **automated before/after eval** that quantifies the improvement.

## The Three Operations

### Ingest
- What goes in: the client's scattered knowledge (6 markdown docs: services, pricing,
  policies, persona, FAQ, booking flow).
- How captured: `cognee.remember(text, dataset_name="angelsitting")` (no session_id →
  permanent graph). Skills are loaded with `content_type="skills"`.
- Code entry point: [`kely_brain/ingest.py`](kely_brain/ingest.py)

### Query + Self-improve
- How users query: `cognee.search(query_type=AGENTIC_COMPLETION, skills=[...], session_id=...)`
  — the agent uses the `memory_search` + `load_skill` tools ([`agent.py`](kely_brain/agent.py)).
- Where feedback comes from: the **kely owner takeover/correction** when an answer is wrong.
- How feedback updates the brain:
  - **Behaviour:** low-scored `SkillRunEntry` → `skill_improvement` proposal (`apply=False`) →
    `improve_skill(apply=True)` rewrites the SKILL.
  - **Knowledge:** `cognee.remember(corrected_fact)` heals the permanent graph.
- Code entry point: [`kely_brain/improve.py`](kely_brain/improve.py)

### Lint
- What linting means: detect duplicate memories and **contradictions** (e.g. a stale 79 € price
  vs the authoritative 89 €), keep the authoritative item, prune the rest by `data_id`
  (`cognee.forget(data_id=..., dataset_id=...)`).
- How it runs: on-demand; reasons over a memory registry (it is NOT told which items are bad).
- Code entry point: [`kely_brain/lint.py`](kely_brain/lint.py)

## Self-Improvement Evidence

Automated, reproducible, judge-readable. Same eval set, scored by an LLM judge, before vs after.
Full data: `out/scorecard_baseline.json`, `out/scorecard_improved.json`, `out/evidence.md`.

**Result: 7/9 (avg 0.78) → 9/9 (avg 0.99)** — every gain traceable to a mechanism, zero regressions.

| Question | Trap | Before | After | Fixed by |
|---|---|---|---|---|
| city | | ✅ 1.00 | ✅ 1.00 | — |
| essential_price | | ✅ 1.00 | ✅ 1.00 | — |
| switch_cancel | | ✅ 1.00 | ✅ 1.00 | — |
| talk_to_sitters | | ✅ 1.00 | ✅ 1.00 | — |
| last_minute | | ✅ 1.00 | ✅ 1.00 | — |
| onboarding | | ✅ 0.90 | ✅ 0.90 | — |
| **languages** | missing_knowledge | ❌ 0.20 | ✅ 1.00 | graph: owner `remember`'d the fact |
| **family_price** | stale_conflict | ❌ 0.00 | ✅ 1.00 | lint: resolved 79 € → 89 € conflict |
| **police_check** | policy_behaviour | ✅ 0.90 | ✅ 1.00 | graph vetting fact + skill rewrite |
| **TOTAL** | | **7/9 · 0.78** | **9/9 · 0.99** | |

### Recorded feedback (the owner takeover that drove a skill rewrite)

```text
selected_skill_id: malika-concierge
error_type: policy_violation
error_message: Never claim sitters are "polizeilich überprüft"/have a Führungszeugnis; approved
               wording is "persönlich interviewt" + "pädagogisch geschult"; offer the free intro call.
feedback: -1.0
success_score: 0.1
```

→ produced a `SkillImprovementProposal` (`apply=False`), then `improve_skill(apply=True)` set the
skill's procedure to the proposed version (status: **applied**). Full before/after procedure diff
in `out/evidence.md`.

### What changed in the brain between runs

```text
Before: graph held both 79 € and 89 € for the Family plan; "languages" unknown; no vetting wording.
After:  lint kept only the authoritative 89 €; languages + vetting facts added; skill rewritten.
```

## Architecture

```
corpus/angelsitting/*.md ──ingest──▶ [ Permanent graph ]  (remember, no session_id)
                                            ▲   │ recall / agentic memory_search
customer turn ─▶ [ Session memory ]─────────┘   ▼
   (remember, session_id=wa_<id>)            kely (Malika) agent answers
        │ improve(session_ids=[…]) distils session → graph
        ▼
owner correction ─▶ SkillRunEntry → proposal(apply=False) → improve_skill(apply=True)  [behaviour]
                 └▶ remember(corrected_fact)                                            [knowledge]
lint ─▶ registry → LLM finds dup/conflict → forget(data_id=…)                           [coherence]
```

### Cognee Cloud (used — `cloud_demo.py`)
We connected to our managed **Cognee Cloud tenant** (Duobingo) via
`cognee.serve(url, api_key)` (X-Api-Key auth; tenant in the URL subdomain) and **host the
Company Brain's permanent knowledge there**: `cloud_demo.py` ingests the AngelSitting corpus +
corrected facts into the tenant (cognified by the Cloud instance) and retrieves them back —
verified grounded answers served from Cloud, e.g. *"Der AngelSitting Family-Tarif kostet 89 €
pro Monat"* and *"AngelSitting ist ausschließlich in Berlin verfügbar."*

**What runs where (honest):** the managed tenant exposes `remember` + `recall` (verified). The
**session-memory tier**, **`improve()` distillation**, and the **`SkillRunEntry → improve_skill`
self-improvement loop** use the full prerelease V2 API and run on **local cognee** — the tenant
returns `404` for `improve` and restricts multi-dataset writes (`403`). So the durable business
brain (ingest + grounded query) lives on Cloud; the self-improvement orchestration is local.
Both use the **same code path** — `config.connect_cloud()` routes everything remote when creds
are present, with zero other changes.

- Permanent graph (no `session_id`): durable business facts, hosted on the Cloud tenant.
- Session memory (`session_id=wa_<id>`) + distillation (`improve(session_ids=[...])`): local tier.

## Agents / Skills

```text
Skill path(s): my_skills/malika-concierge/SKILL.md, my_skills/qa-answerer/SKILL.md
Roles:
  - Querier:  malika-concierge (customer-facing, Sie-form concierge)
  - Critic:   LLM judge (kely_brain/judge.py) scores answers vs golden
  - Linter:   kely_brain/lint.py (dedupe + conflict resolution)
```

## Reproduction

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e .
cp .env.example .env   # add LLM_API_KEY
uv run python demo.py
```

Environment variables required:

```text
LLM_API_KEY           # (OPENAI_API_KEY is auto-mirrored into it)
COGNEE_SERVICE_URL    # optional — Cognee Cloud instance
COGNEE_API_KEY        # optional — Cognee Cloud key
```

## Demo

- Local: `uv run python demo.py` (prints before/after + writes `out/evidence.md`).
- 3-minute pitch outline:

```text
1. Problem: every kely client's knowledge is scattered; the agent can't self-correct.
2. Ingest: AngelSitting's docs → the brain.
3. Query (before): stale price, missing fact, unsafe claim → baseline score.
4. Self-improve: one owner correction rewrites the SKILL + heals the graph.
5. Lint: resolves the price conflict + prunes a duplicate.
6. Query (after): same questions, higher score. Next: ship to live kely clients.
```

## Links

- Repo: https://github.com/Paulson237/kelyy
- Writeup: this file + `EVIDENCE.md` (generated `out/evidence.md`)

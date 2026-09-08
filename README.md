# Neva

A Turkish-language CBT self-help assistant that shows its work.

**Live:** [askneva.com](https://askneva.com) · Free, no account required

Most mental-health chatbots are a system prompt wrapped around a frontier model. Neva
is a retrieval-grounded pipeline over a clinician-reviewed knowledge base, with a
safety classifier in front of it and an output critic behind it. Every answer exposes
the card it was built from, and every card is version-locked to a clinical review.

---

## Why this is hard

Mental-health support has a property most consumer AI doesn't: **the cost of a
plausible-but-wrong answer is asymmetric.** A recipe app that hallucinates wastes an
evening. An assistant that normalises chest pain as "just anxiety", or keeps talking
through a suicidal disclosure, does real harm.

That constraint drove nearly every design decision here:

| Constraint | Consequence |
|---|---|
| Model must not invent clinical content | Retrieval over 180 reviewed cards; the composer sees cards, not free rein |
| Model must not miss a crisis signal | Deterministic rule layers run **before** the LLM and can hard-stop the pipeline |
| Model must not slip past review | Every generated answer is critiqued against 8 rules; failures trigger rewrite, then template fallback |
| A card's approval must not outlive its content | Clinical sign-off is bound to a content hash; edit the text and approval drops |
| Users deserve to see the machinery | Every turn ships a transparency payload: route, module, cards used, critic verdict |

---

## Architecture

```
                      ┌──────────────────────────────────────────┐
   user message ───▶  │  1. SAFETY CLASSIFIER      (3 layers)    │
                      │     L1 hard rules   47 exact phrases     │
                      │     L2 concept rules 57 concepts /       │
                      │                      106 combinations    │
                      │     L3 embedding fallback + LLM verify   │
                      └───────────────┬──────────────────────────┘
                                      │ allow_cbt=False → hard stop,
                                      │ safety template, no generation
                                      ▼
                      ┌──────────────────────────────────────────┐
                      │  2. INTENT           Haiku, 18 modules   │
                      │  3. RETRIEVAL        vector seeds        │
                      │       + Neo4j graph enrichment           │
                      │  4. COMPOSER         Sonnet, card-bound  │
                      └───────────────┬──────────────────────────┘
                                      ▼
                      ┌──────────────────────────────────────────┐
                      │  5. OUTPUT CRITIC        8 hard rules    │
                      │     fail → rewrite once                  │
                      │     fail again → safety card template    │
                      └───────────────┬──────────────────────────┘
                                      ▼
                            response + transparency payload
                                      │
                      (background) 6. PROFILE EXTRACTION — Haiku
```

**The safety classifier runs first and is mostly not a model.** Layers 1 and 2 are
deterministic: exact multi-word phrases, and compositional rules that fire on feature
combinations (e.g. `pain_axial_limb` + `systemic_fever` → medical referral, not CBT).
Layer 3 catches paraphrases the rules miss via embedding similarity against concept
anchors, then asks an LLM to confirm — but a Layer 3 match alone never *lowers* a
risk level set by Layers 1–2.

Three gates come out of it:

- `allow_cbt=False` — hard stop. No generation. Safety card template only.
- `allow_cbt=True, blocks_exercise=True` — supportive reply, no technique offered.
  For moments when handing someone a breathing exercise would be tone-deaf.
- `scope_boundary` — outside the 18 modules. Neva says so instead of improvising.

---

## The knowledge base is the product

```
cards/cbt_cards.jsonl        180 cards · 18 modules · 10 each
cards/safety_cards.jsonl      19 safety routing cards
registry/source_registry.csv 171 sources, every card cited
rules/safety_trigger_rules.json   47 hard rules · 57 concepts · 106 groups
```

Card types: 52 technique · 51 psychoeducation · 40 exercise · 18 safety ·
17 self-assessment · 2 in-attack.

Sources are real clinical literature — NICE and APA guidelines, Cochrane-style
systematic reviews, seminal papers (Kroenke 2001 for PHQ-9, Spitzer 2006 for GAD-7),
NHS patient guidance, and established self-help workbooks. Content is **synthesised,
not copied**; the registry records licence and permitted use per source.

### Version-locked clinical review

All 199 cards were read and approved by a clinical psychologist on 4 September 2026.
The interesting part is what happens *after* approval:

```jsonc
{
  "id": "exam_thoughts_004",
  "review_status": "clinician_reviewed",
  "clinician_reviewed_at": "2026-09-04",
  "reviewed_content_hash": "1f9c55aa5abe68ce"   // sha256(title + content)[:16]
}
```

`scripts/audit_review_status.py` recomputes every hash. If a card's text changed
after sign-off, the hash no longer matches and the audit fails. This runs as a
**test**, so drifted content turns the suite red:

```python
def test_no_card_changed_after_review():
    drifted, _, _, _ = audit()
    assert drifted == [], "approval is void; request re-review"
```

Clinical approval that silently survives an edit isn't approval. This makes that
impossible to do by accident.

---

## Transparency as a feature, not a disclosure

Every response carries the reasoning that produced it, and the UI surfaces it under a
**"how was this made"** panel on each message:

```json
{
  "safety":  { "route": "cbt_support", "allow_cbt": true,
               "highest_risk": "low", "blocks_exercise": false },
  "intent":  { "module": "exam_anxiety", "subintent": "reassurance_seeking",
               "confidence": 0.82 },
  "retrieved_card_ids": ["exam_thoughts_004", "ga_4c_008"],
  "critic":  { "passed": true, "rewrites": 0, "used_fallback": false },
  "timing_ms": { "safety": 41, "intent": 380, "retrieval": 55, "compose": 2100 }
}
```

The landing page turns this into an interactive demo: pick a thought, watch the
pipeline resolve it step by step. Same panel, same data — just pointed outward.

Because card IDs are in the payload, the client can map a used card to the matching
standalone tool. When an answer draws on a thought-record card, the message renders a
link to the thought-record exercise. The mapping is card-ID based, not a guess at what
the model said — and a test asserts every mapped ID still exists in the knowledge base,
so a renamed card can't silently kill the link.

---

## Product decisions worth defending

**No streaks, badges, or notifications.** Stated on the landing page and in
onboarding, and enforced in the system prompt's "features that do not exist" list.
Engagement mechanics are the obvious growth lever and the wrong one here: a broken
streak produces guilt, and "open the app even on a bad day" is not a healthy
instruction for someone with anxiety. Progress is instead anchored to measurement
(PHQ-9/GAD-7), what actually helped (`coping_tried`), and milestones — *firsts*, never
frequency.

**Conversations end.** A session follows an arc (exploration → formulation → work →
consolidation) and Neva offers to close at a good point rather than maximising turns.
A 6-hour gap starts a new sitting and resets the arc.

**The journal is invisible to the model.** Users write daily entries; the LLM never
sees them. The system prompt forbids "let's look at your journal" precisely because
that data never reaches it — a feature the model *could* plausibly claim to have.

**Honesty about cross-border data.** The privacy page says plainly that messages are
processed outside Turkey (Anthropic in the US, database in Frankfurt), that Turkey has
no adequacy decision for any country, and that if this bothers you the right call is
not to use Neva. Redaction strips identifiers but the content itself is health data
and it does leave. Saying so is the only defensible position.

---

## Engineering

**Stack** — FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · Neo4j Aura ·
Next.js 14 (App Router) · TypeScript · Tailwind · Anthropic API (Sonnet + Haiku)

**Scale** — ~15.4k lines Python · ~9.2k lines TypeScript · 46 endpoints ·
14 migrations · 166 tests

### Auth

Access token (15 min, JWT, memory only — never localStorage) plus refresh token
(30 days, random, SHA-256 hashed at rest, `httpOnly Secure SameSite=Lax` cookie scoped
to `/auth`). Rotation on every refresh with **reuse detection**: presenting an already
rotated token invalidates the entire family, on the assumption it was stolen.

Two subtleties that only show up in production:

- **Revoked rows can't be garbage-collected on expiry.** Reuse detection needs the old
  token's record to still exist. Two retention windows: expired-and-unused rows go at
  30 days, revoked rows are kept 90.
- **Concurrent refreshes are normal, not attacks.** Two tabs racing produced identical
  requests that looked like token theft and logged users out of everything. A 30-second
  grace window returns a distinct `RACE` outcome (HTTP 409, cookie preserved) rather
  than nuking the session.

### Testing

166 tests, weighted toward the things that would actually hurt someone:

- **Access control** — cross-user isolation on every user-scoped endpoint; an
  anonymous caller holding a valid session ID still cannot read account-scoped records
- **Safety classification** — layer precedence, escalation, confirmation flow
- **Token lifecycle** — rotation, reuse detection, race grace, cookie flags
- **Content integrity** — review-status drift, card counts matching the privacy page,
  exercise links resolving to real cards

Several tests exist because they caught a real defect. `test_history_survives_new_session`
guards a bug where assessments were stored without a `user_id`, so the trend chart
silently reset on every new conversation. `test_no_empty_session_is_created` guards a
fix where a non-nullable FK forced phantom empty conversations into users' history.

---

## Known gaps

Kept honest, in priority order:

1. **Rate limiting is configured but not wired.** `SlowAPIMiddleware` is never
   registered, so `default_limits` never fire — and `get_remote_address` behind the
   platform proxy would bucket all users together anyway. `/chat` is unauthenticated
   and calls a paid API. This is the launch blocker.
2. **Account deletion is untested** despite being a stated legal commitment.
   `exercise_entries` and `journal_entries` rely on database-level cascade without
   ORM relationships backing it up.
3. **Migrations never run against PostgreSQL in CI.** Tests use SQLite and skip
   Alembic entirely. This has already caused one production failure (a `CHAR(36)`
   foreign key that SQLite accepted and PostgreSQL rejected).
4. **The conversation-state classifier sits at 84%, and the remaining errors are
   uneven.** Process cards are retrieved by a `conversation_state` label. Measured
   over `evals/process_state_test_set.jsonl` (87 labelled Turkish cases, 17 states):

   | run | accuracy | what changed |
   |---|---|---|
   | first | 48/87 (55%) | baseline |
   | second | 73/87 (84%) | few-shot examples fixed |

   The first run's failure was not ambiguity. The field had been added to the output
   schema but to none of the 41 few-shot examples, so the model omitted it and the
   parser defaulted to `neutral` — four states scored 0/5 and 25 of 39 errors were
   that single bug. The measurement also falsified the hypothesis that drove it:
   the label set was not too large.

   Raw accuracy hides what matters, so the runner grades errors by behavioural cost.
   Of the 14 remaining: 6 high (the wrong move — e.g. missing `reassurance_seeking`
   means giving reassurance, which maintains the anxiety cycle), 6 medium, 2 low
   (adjacent cards that produce a similar move). Two definitions still over-absorb
   (`vague`, `withdrawn`) and have since been narrowed, unmeasured.

5. No data export (deletion exists, portability doesn't), no email change, no error
   monitoring, no mobile client.

---

## Running locally

```bash
# Backend
pip install -r requirements-api.txt
alembic upgrade head
uvicorn api.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Knowledge graph (optional — retrieval degrades to vector-only without it)
python -m graph.migrate

# Checks
pytest tests -q
python scripts/audit_review_status.py --strict
```

Set `CBT_LLM_PROVIDER=mock` to run the whole pipeline without an API key.

Detailed setup: [`BACKEND_SETUP.md`](BACKEND_SETUP.md) ·
Deployment: [`DEPLOY.md`](DEPLOY.md)

---

## Disclaimer

Neva is not a therapist, a clinician, or an emergency service, and does not diagnose.
It is a self-help tool built on reviewed material. In Turkey the emergency number is
**112**. If you are struggling, talking to a real person is the better step.

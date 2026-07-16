# Thai Farmer LINE LLM Advisory Agent

Guardrailed LLM agent that lets **farmers in Thailand chat over LINE**. It answers
general questions conversationally, and for specific agriculture questions it answers
**only from a curated FAQ knowledge base** (retrieval-augmented generation) with source
citations. Admins review every interaction in an **admin portal**.

This repository is the reference implementation of the architecture described in
[docs/data-architecture.md](docs/data-architecture.md) (PDF: [docs/data-architecture.pdf](docs/data-architecture.pdf)).

## Key properties

- **Grounded-only domain answers** — a domain reply is blocked unless it carries at least
  one citation to a *published* FAQ chunk above a confidence threshold.
- **Anti-misinformation guardrails** — high-risk topics (pesticide dosage, medical, legal,
  financial) get a safe templated response + escalation instead of a generated answer.
- **Runs with zero external services** — defaults to SQLite, a deterministic hashing
  embedder, and a stub LLM, so you can run it locally with no API keys. Swap in
  Postgres/pgvector, real embeddings, and a real LLM via environment variables.
- **Auditable** — every admin view of conversation content writes an `audit_event`.

## Architecture (runtime)

```
LINE ──webhook──> Channel Gateway ──> Orchestrator ──┬─> LLM (general / grounded)
                     (sig verify)     (intent+safety) ├─> Retrieval ──> KB (FAQ + vectors)
                                                      └─> Conversation Store ──> Admin Portal
```

## Quick start

```bash
cd thai-farmer-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: fill in LINE / LLM keys
uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

On first start the DB is created and seeded with sample Thai agriculture FAQs.

### Try it without LINE

```bash
# simulate an inbound farmer message
curl -s -X POST http://127.0.0.1:8000/webhook/simulate \
  -H 'Content-Type: application/json' \
  -d '{"line_user_id":"U_demo","text":"ข้าวใบเหลืองควรทำอย่างไร"}' | python3 -m json.tool
```

### Admin portal

Open http://127.0.0.1:8000/admin (send the `ADMIN_TOKEN` as `?token=` or the
`X-Admin-Token` header; default token is in `.env.example`).

- `/admin/conversations` — browse sessions & messages, route, citations.
- `/admin/faq` — view/add FAQ entries (adding re-embeds automatically).

## LINE setup (production)

1. Create a LINE Messaging API channel; set the webhook URL to
   `https://<host>/webhook/line`.
2. Put `LINE_CHANNEL_SECRET` and `LINE_CHANNEL_ACCESS_TOKEN` in `.env`.
3. The webhook verifies the `X-Line-Signature` HMAC and replies via the LINE Reply API.

## Swapping the defaults

| Concern | Default | Production | Env |
|---|---|---|---|
| Database | SQLite | PostgreSQL (+pgvector) | `DATABASE_URL` |
| Embeddings | hashing (offline) | OpenAI-compatible | `EMBEDDINGS_PROVIDER`, `OPENAI_API_KEY` |
| LLM | stub (extractive) | Claude / OpenAI | `LLM_PROVIDER`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` |

## Using Claude (Anthropic)

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...          # from console.anthropic.com
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

> **Important:** the Messages API needs an **Anthropic API key with credits**, obtained
> from console.anthropic.com. A **claude.ai Pro/Max subscription does not grant API
> access** — they are billed separately. The guardrails (grounded-only answers,
> citations, high-risk refusal) are enforced in the orchestrator regardless of provider,
> so Claude cannot answer domain questions outside the FAQ knowledge base.
>
> Anthropic has no embeddings endpoint, so retrieval keeps using the offline hashing
> embedder (or point `EMBEDDINGS_PROVIDER=openai` at an embeddings model).

## Deploy to Render

This repo includes [render.yaml](render.yaml), a Render Blueprint that provisions the
web service **and** a managed PostgreSQL database (Singapore region — closest to Thailand).

1. Push this repo to GitHub.
2. In Render: **New + → Blueprint**, select the repo. Render reads `render.yaml`.
3. After the first deploy, set the secret env vars (marked `sync: false`) in the
   dashboard: `ANTHROPIC_API_KEY`, `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`.
   `ADMIN_TOKEN` is auto-generated; `DATABASE_URL` is auto-injected.
4. Set the LINE webhook URL to `https://<your-service>.onrender.com/webhook/line`.
5. Health check: `https://<your-service>.onrender.com/health`.

The app converts Render's `postgres://` URL to the psycopg driver automatically and
creates/seeds tables on first boot. Postgres is used (not SQLite) so data persists
across Render's ephemeral filesystem.

## Layout


```
app/
  main.py            FastAPI app + startup (create tables, seed)
  config.py          env-driven settings
  database.py        SQLAlchemy engine/session
  models.py          farmer, consent, session, message, faq_doc, faq_chunk, citation, audit_event
  embeddings.py      embedding providers (hashing fallback + OpenAI)
  llm.py             LLM providers (stub + OpenAI)
  retrieval.py       vector search over published FAQ chunks
  guardrails.py      intent classification + high-risk detection
  orchestrator.py    routing, grounding, safety decisions
  line_client.py     signature verification + reply API
  seed.py            sample Thai agriculture FAQ
  routers/webhook.py LINE webhook + local simulate endpoint
  routers/admin.py   admin portal + JSON API + audit
  templates/         admin HTML
```

> Demo defaults are for local development only. Review §9 (PDPA) and §10 (retention) of the
> data architecture before handling real farmer data.

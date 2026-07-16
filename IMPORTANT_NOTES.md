# IMPORTANT NOTES — Thai Farmer LINE LLM Agent

Read before running, demoing, or deploying. Concise, critical items only.

## What this is
- Guardrailed LLM agent: Thai farmers chat over **LINE**; general questions answered
  conversationally, **agriculture questions answered ONLY from a curated FAQ knowledge
  base (RAG) with citations**; admins review every interaction.
- Reference implementation of `docs/data-architecture.md`
  (PDFs: `docs/data-architecture.pdf` concise, `docs/data-architecture-booth.pdf` detailed).

## Runs out-of-the-box (no keys, no external services)
- Defaults: **SQLite + offline hashing embedder + stub LLM**. Start:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  uvicorn app.main:app --reload
  ```
- DB is auto-created and seeded with sample Thai agriculture FAQs on first boot.
- Try without LINE:
  ```bash
  curl -s -X POST http://127.0.0.1:8000/webhook/simulate \
    -H 'Content-Type: application/json' \
    -d '{"line_user_id":"U_demo","text":"ข้าวใบเหลืองควรทำอย่างไร"}'
  ```
- Admin portal: `http://127.0.0.1:8000/admin?token=<ADMIN_TOKEN>`
  (default token in `.env.example`).
- Smoke test: `python -m tests.smoke_test` (must print `SMOKE TEST PASSED`).

## CRITICAL: Claude subscription is NOT API access
- The Messages API needs an **Anthropic API key with credits** from
  console.anthropic.com. A **claude.ai Pro/Max subscription does not authenticate the
  API** — billed separately.
- Enable Claude: `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=sk-ant-...`.
- Anthropic has **no embeddings endpoint** → retrieval stays on the hashing embedder
  (or set `EMBEDDINGS_PROVIDER=openai`).

## Known limitation — offline embedder retrieval quality
- The default **hashing embedder** matches on character n-grams and can produce
  **false-positive grounding** (e.g. an unrelated question mapped to a FAQ).
- Fixes: raise `RETRIEVAL_MIN_SCORE` (default 0.18), or use a real embedding model in
  production. This is expected for the demo; do not present it as production retrieval.

## Guardrail invariants (do not weaken)
1. High-risk topics (pesticide dosage, medical, legal, financial) → **refused with safe
   template + escalate**, never generated.
2. Domain answer → **grounded + cited above threshold, or refused** (no hallucination).
3. Only `faq_doc.status=published` within `valid_from/valid_to` is retrievable.
4. Source attribution is appended to grounded answers.
- Enforced in `app/orchestrator.py`, independent of the LLM provider.

## Deploy to Render (see render.yaml)
- Blueprint provisions the web service **+ managed PostgreSQL** (Singapore region).
- After first deploy set secrets in dashboard: `ANTHROPIC_API_KEY`,
  `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`. `ADMIN_TOKEN` is auto-generated;
  `DATABASE_URL` auto-injected (`postgres://` is normalized to the psycopg driver).
- LINE webhook URL: `https://<service>.onrender.com/webhook/line`.
- Postgres (not SQLite) is used in prod so data persists across Render's ephemeral disk.

## Security / PDPA (Thailand)
- Stores **pseudonymous** `line_user_id` only — no phone/national ID.
- Webhook verifies `X-Line-Signature` (HMAC-SHA256) + idempotency dedupe on
  `line_message_id`.
- Consent is purpose-based/versioned; erasure cascades; every admin view of conversation
  content writes an append-only `audit_event`.
- If using an external LLM, redact PII before egress and keep a DPA; prefer in-region.
- **Sample FAQ content is illustrative only** — real content must be authored/reviewed by
  domain experts and attributed to authoritative sources (DOA / Rice Dept).

## What is NOT included / open items
- Voice/STT, human-in-the-loop live handoff, multi-tenant, Redis wiring (session TTL
  logic present, Redis backend not required for demo), production embedding/LLM keys.
- Confirm legal audit-retention period with counsel.

## Package excludes
- `.venv/`, `__pycache__/`, `*.db`, `.env`, `.git/` are excluded from the zip.
  Copy `.env.example` → `.env` and fill values as needed.

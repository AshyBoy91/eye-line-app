"""Generate docs/conference_qa.pdf — 30 Q&As for the Bangkok agriculture conference.
Run: .venv\Scripts\python tools\generate_qa_pdf.py
"""
from __future__ import annotations
import asyncio
from pathlib import Path

QA = [
    # ── Technical Architecture ─────────────────────────────────────────────
    (
        "What technology stack powers this system?",
        "The system is built with <b>FastAPI</b> (Python web framework), <b>SQLAlchemy</b> for database ORM, "
        "<b>PostgreSQL</b> on Render for production storage, and <b>httpx</b> for async HTTP calls. "
        "It is deployed on <b>Render</b> (Singapore region) for low latency to Thailand. "
        "The AI layer uses Anthropic's <b>Claude Sonnet</b> via the Messages API."
    ),
    (
        "How does the system connect to LINE?",
        "LINE uses a <b>webhook model</b>: when a farmer sends a message, LINE's platform POSTs a JSON "
        "event to our server at <code>/webhook/line</code>. The server verifies the request is genuinely "
        "from LINE using an <b>HMAC-SHA256 signature</b> (X-Line-Signature header), then processes the "
        "message and replies using LINE's Reply API with the farmer's one-time reply token."
    ),
    (
        "Where is the system hosted and how reliable is it?",
        "The system runs on <b>Render</b> (cloud platform, Singapore region) with a <b>managed PostgreSQL</b> "
        "database. The free tier has a ~50-second cold start after inactivity; the paid tier eliminates this. "
        "Render provides automatic TLS, health checks, and rollback deploys. The webhook endpoint has "
        "idempotency protection so LINE's automatic retries do not create duplicate responses."
    ),
    (
        "How does the system store farmer conversations?",
        "Every inbound and outbound message is stored in PostgreSQL with full metadata: intent classification, "
        "route (grounded/refused/escalated), confidence score, model used, latency, and citation links. "
        "Farmers are stored by <b>pseudonymous LINE user ID only</b> — no phone numbers or national IDs. "
        "Sessions group messages with a 30-minute idle window."
    ),
    (
        "Can this system scale to serve all Thai farmers?",
        "The current architecture is stateless and horizontally scalable — Render can run multiple instances "
        "behind a load balancer. The database bottleneck can be addressed by upgrading to a paid PostgreSQL "
        "plan with connection pooling (PgBouncer). For national scale, a pgvector index would replace the "
        "in-memory cosine similarity search, and the LINE Channel would need a verified Official Account."
    ),

    # ── AI & Knowledge Base ────────────────────────────────────────────────
    (
        "Which AI model is used and why Claude?",
        "<b>Anthropic Claude Sonnet 4.5</b> is used via the Messages API. Claude was chosen for its strong "
        "Thai language comprehension, instruction-following reliability, and its ability to stay grounded "
        "when given reference context. Critically, the guardrail policy is enforced in application code "
        "<i>independently</i> of the model — so Claude is a response generator, not a policy-maker."
    ),
    (
        "What is RAG and why was it chosen over a general AI chatbot?",
        "<b>Retrieval-Augmented Generation (RAG)</b> means the AI answers only from retrieved, verified "
        "documents — not from its training data alone. For agriculture, this is essential: a general AI "
        "might confidently generate plausible but wrong advice. With RAG, every answer is grounded in "
        "expert-reviewed FAQ entries with source citations, and if no relevant document exists above the "
        "confidence threshold, the system refuses rather than guesses."
    ),
    (
        "How is the knowledge base created and maintained?",
        "The knowledge base consists of <b>FaqDoc</b> entries with categories (rice, soil, pests, crop, "
        "government_incentive, false_news_alert). Each document has a title, Thai body text, source "
        "attribution, validity window, and status (draft/published/archived). Admins create and edit "
        "entries via the password-protected <b>/admin/faq</b> portal. New entries are immediately chunked "
        "and embedded for retrieval. <i>Production content must be authored by domain experts from "
        "authoritative sources such as the Department of Agriculture or Rice Department.</i>"
    ),
    (
        "What happens when a question has no answer in the knowledge base?",
        "The retrieval step returns the top-K FAQ chunks scored by cosine similarity. If no chunk exceeds "
        "the minimum confidence threshold (default 0.18), the system returns a fixed Thai refusal message: "
        "<i>'ยังไม่มีข้อมูลที่ตรงกับคำถามนี้ในคลังความรู้'</i> and suggests the farmer contact a local "
        "agricultural extension officer. The AI model is never called in this case — no hallucination risk."
    ),
    (
        "How accurate are the AI answers?",
        "Accuracy depends on knowledge base quality. The current demo uses a hashing embedder (character "
        "n-gram similarity) which can produce false-positive matches; the minimum score threshold mitigates "
        "this. In production, replacing the embedder with a Thai-capable model (e.g. OpenAI "
        "text-embedding-3-small) significantly improves precision. Every answer includes a source citation "
        "so admins and farmers can verify the information independently."
    ),

    # ── Guardrails & Safety ────────────────────────────────────────────────
    (
        "How does the system prevent harmful advice about pesticide dosages?",
        "Pesticide dosage keywords (e.g. <i>ปริมาณยา, อัตราการใช้สารเคมี, พาราควอต</i>) trigger a "
        "<b>hard safety gate</b> in the orchestrator <i>before</i> any retrieval or AI generation occurs. "
        "The system returns a fixed template refusing the specific request and directing the farmer to "
        "contact an agricultural extension officer. This gate cannot be bypassed by any prompt."
    ),
    (
        "What topics does the system absolutely refuse to answer?",
        "Four categories are hard-refused: <b>chemical/pesticide dosage</b> (exact quantities, mixing "
        "instructions), <b>medical/human health</b> advice, <b>legal/regulatory</b> advice, and "
        "<b>financial</b> advice (loans, investments). These are detected by a keyword list maintained "
        "in <code>app/guardrails.py</code> covering both Thai and English terms. The list is auditable "
        "and extensible by domain experts without code changes."
    ),
    (
        "Can the AI hallucinate or invent agricultural facts?",
        "<b>No</b> — for domain questions. The orchestrator enforces that: (1) answers must come from "
        "retrieved FAQ chunks, (2) at least one citation above the confidence threshold is required, "
        "and (3) the source is appended to every grounded answer. If those conditions cannot be met, "
        "the system refuses. For general small-talk, Claude answers conversationally with no grounding "
        "requirement, but small-talk cannot carry agricultural advice (intent classifier prevents this)."
    ),
    (
        "Who reviews the conversations for quality?",
        "All conversations are visible to authorised admins in the <b>/admin/conversations</b> portal. "
        "Each message is tagged with its route (grounded/refused/escalated/smalltalk) and confidence "
        "score. Every admin view of conversation content writes an append-only <b>AuditEvent</b> record "
        "for PDPA accountability. In a production deployment, a designated expert (e.g. from the "
        "Department of Agriculture) would review flagged or low-confidence interactions weekly."
    ),
    (
        "What happens when a high-risk question is asked?",
        "The route is set to <b>'refused'</b> with a safe Thai template. The response never reveals "
        "partial information or hedges — it unconditionally directs the farmer to a human expert. "
        "The interaction is logged with <code>intent='high_risk'</code> so admins can monitor for "
        "patterns (e.g. a surge in pesticide-dosage questions might indicate a regional pest outbreak "
        "that warrants proactive expert communication)."
    ),

    # ── LINE Integration & User Experience ────────────────────────────────
    (
        "Why was LINE chosen as the communication platform?",
        "LINE is <b>Thailand's dominant messaging app</b> with over 47 million active users, including "
        "extensive rural adoption. Farmers already use it daily — zero onboarding friction. The Messaging "
        "API is mature, well-documented, and supports rich menus (persistent button panels), broadcast "
        "messages, and webhook-based bot integration with strong security (HMAC-SHA256 signature verification)."
    ),
    (
        "Do farmers need to download or install anything new?",
        "<b>No.</b> Farmers simply add the bot's LINE ID (<b>@643txfqa</b>) as a friend — the same way "
        "they add any contact. From that moment they can type questions in Thai and receive answers "
        "instantly. A persistent Rich Menu panel appears at the bottom of the chat with one-tap shortcuts "
        "for common topics."
    ),
    (
        "How fast does the bot respond?",
        "With Claude Sonnet 4.5 and a warm server, end-to-end latency (LINE → server → Claude → LINE) is "
        "typically <b>3–8 seconds</b>. The free Render plan has a cold-start delay (~50 seconds) after "
        "inactivity; the paid plan eliminates this. Database queries are indexed and the health-check "
        "endpoint keeps the service warm during active periods."
    ),
    (
        "What languages does the system support?",
        "The knowledge base, AI prompts, and responses are in <b>Thai (ภาษาไทย)</b>. The system prompt "
        "instructs Claude to respond in polite, accessible Thai. The intent classifier and guardrail "
        "keyword lists include both Thai and English terms, so farmers who mix languages are handled "
        "correctly. Full multilingual knowledge base support (e.g. Northern Thai dialects) is a future "
        "enhancement."
    ),
    (
        "What happens if a farmer asks about something outside agriculture?",
        "The intent classifier checks for domain keywords. If none are found, the message is routed to "
        "<b>'smalltalk'</b> — Claude answers conversationally (greetings, general chat) without RAG. "
        "Agriculture keywords trigger RAG retrieval. This keeps responses friendly while ensuring "
        "agricultural advice is always grounded. A farmer asking 'สวัสดีครับ' gets a warm welcome; "
        "a farmer asking about rice disease gets a verified, cited answer."
    ),

    # ── Privacy & Legal (PDPA) ────────────────────────────────────────────
    (
        "What personal data does the system store?",
        "The system stores only the <b>pseudonymous LINE user ID</b> (a string like 'U1234abcd' assigned "
        "by LINE — not a real name, phone, or national ID). Message content, intent, route, and "
        "timestamps are stored for service quality and admin review. No biometric, location, or "
        "financial data is collected. Farmers' display names and province can optionally be stored "
        "if explicitly provided, but are not required."
    ),
    (
        "How does the system comply with Thailand's Personal Data Protection Act (PDPA)?",
        "PDPA compliance is built-in: (1) <b>Purpose-based consent</b> is recorded at first contact; "
        "(2) data is <b>pseudonymised</b> (LINE user ID only); (3) every admin view of conversation "
        "content writes an append-only <b>AuditEvent</b>; (4) erasure is supported with cascade "
        "deletion; (5) data is stored in Singapore (Render), which requires a DPA for cross-border "
        "transfer — this should be formalised before national deployment."
    ),
    (
        "Can farmers request deletion of their data?",
        "<b>Yes.</b> The data model supports erasure: deleting a <b>Farmer</b> record cascades to all "
        "sessions, messages, citations, and consent records. A formal erasure request workflow (e.g. "
        "farmer sending a specific message like 'ขอลบข้อมูล') can be implemented as an extension. "
        "The audit trail for admin actions is retained separately as required for accountability."
    ),
    (
        "Is farmer conversation data shared with the government or third parties?",
        "<b>No</b> by default. Conversation content is only accessible to authorised admins via the "
        "password-protected portal. If using an external LLM (Claude), message text is sent to "
        "Anthropic's API — PII should be redacted before egress in a production deployment, and a "
        "Data Processing Agreement with Anthropic should be in place. The system is designed so the "
        "LLM provider can be swapped to an in-region option if data sovereignty requires it."
    ),
    (
        "What is the data retention policy?",
        "The current implementation does not enforce automatic deletion — all records persist until "
        "manually removed. For production deployment, a retention policy (e.g. delete conversations "
        "older than 2 years, retain audit events for 5 years as required by Thai accounting law) "
        "should be implemented and confirmed with legal counsel. The data architecture supports "
        "timestamped records on all tables to enable time-based purging."
    ),

    # ── Daily Briefing ─────────────────────────────────────────────────────
    (
        "What is the daily briefing and how does it work?",
        "On each farmer's <b>first message of the day</b> (Bangkok time), the system automatically prepends "
        "a briefing to the reply. The briefing contains three parts: (1) <b>Chiang Mai weather forecast</b> "
        "(temperature, humidity, conditions via OpenWeatherMap API); (2) <b>government incentives</b> — "
        "latest subsidies and programs pulled from the knowledge base; (3) <b>false-news alerts</b> — "
        "circulating misinformation warnings curated by admins. This ensures farmers receive proactive, "
        "relevant information without needing to ask."
    ),
    (
        "How are government incentive and false-news entries kept up to date?",
        "Admins log in to the <b>/admin/faq</b> portal and add or archive entries under the categories "
        "<code>government_incentive</code> and <code>false_news_alert</code>. Each entry supports a "
        "<b>valid_from / valid_to</b> date window, so seasonal programs or time-limited alerts expire "
        "automatically. New entries are immediately embedded for retrieval and appear in the next day's "
        "briefing. No technical knowledge is required — the admin portal is a simple web form."
    ),

    # ── Impact & Future ────────────────────────────────────────────────────
    (
        "How many farmers can this system realistically help?",
        "Thailand has approximately <b>8.6 million farming households</b>. The LINE platform reaches "
        "rural areas with smartphone penetration. The current system can handle hundreds of concurrent "
        "users per instance and scales horizontally. The knowledge base currently covers rice, soil, "
        "pests, cassava, and sugarcane — expanding to Thailand's top 20 crops would address the "
        "majority of smallholder needs."
    ),
    (
        "What is the plan to expand and improve the knowledge base?",
        "The roadmap includes: (1) partnering with the <b>Department of Agriculture</b> and the "
        "<b>Rice Department</b> to contribute authoritative, peer-reviewed content; (2) replacing "
        "the hashing embedder with a Thai-language embedding model for better retrieval precision; "
        "(3) adding multimedia support (photos of plant disease); (4) building a structured review "
        "workflow so domain experts can approve draft entries before publication."
    ),
    (
        "Could this model be replicated for other provinces or crops?",
        "<b>Yes</b> — the system is crop-agnostic. The knowledge base categories, guardrail keyword "
        "lists, and daily briefing sources are all configurable via the admin portal without code "
        "changes. A separate deployment for Southern Thailand (rubber, palm oil) or the Northeast "
        "(cassava, sugarcane) would require a localised knowledge base and potentially dialect-aware "
        "language handling, but the core architecture is identical."
    ),
    (
        "How will the success of this project be measured?",
        "Key metrics include: (1) <b>engagement rate</b> — daily active farmers and questions per user; "
        "(2) <b>grounding rate</b> — percentage of domain questions answered with citations vs refused; "
        "(3) <b>escalation rate</b> — high-risk question frequency (proxy for misinformation exposure); "
        "(4) <b>knowledge base coverage</b> — questions with no match, indicating gaps to fill; "
        "(5) qualitative <b>farmer satisfaction</b> through follow-up surveys. All metrics are "
        "derivable from the existing conversation logs."
    ),
    (
        "What are the next development milestones?",
        "Priority next steps: (1) <b>Formal partnership</b> with the Department of Agriculture for "
        "authoritative content; (2) <b>Thai embedding model</b> integration for production-quality "
        "retrieval; (3) <b>Multi-media support</b> — farmers can send a photo of a diseased plant; "
        "(4) <b>Human-in-the-loop escalation</b> — escalated questions routed to an expert queue; "
        "(5) <b>Offline resilience</b> — cached daily briefings for areas with intermittent connectivity; "
        "(6) nationwide LINE Official Account verification."
    ),
]

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
  body { font-family: 'Sarabun', 'Segoe UI', Arial, 'Noto Sans Thai', sans-serif; margin: 0; padding: 40px 52px;
         color: #1b2733; background: #fff; font-size: 13px; line-height: 1.6; }
  .cover { text-align: center; padding: 60px 0 80px; border-bottom: 3px solid #2a9d8f; margin-bottom: 48px; }
  .cover h1 { font-size: 28px; color: #0f4c5c; margin: 0 0 8px; }
  .cover .sub { font-size: 16px; color: #2a9d8f; font-weight: 600; }
  .cover .meta { margin-top: 28px; font-size: 13px; color: #6b7b86; }
  h2 { font-size: 14px; color: #0f4c5c; background: #e8f3f1; padding: 8px 14px;
       border-left: 4px solid #2a9d8f; margin: 28px 0 6px; border-radius: 0 6px 6px 0; }
  .section-header { font-size: 17px; font-weight: 700; color: #fff; background: #0f4c5c;
                    padding: 10px 16px; margin: 40px 0 16px; border-radius: 8px; }
  .q { color: #0f4c5c; font-weight: 700; font-size: 14px; margin: 0 0 6px; }
  .a { color: #1b2733; margin: 0 0 6px 14px; }
  .item { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #e8ecee; }
  .item:last-child { border-bottom: none; }
  .num { display: inline-block; background: #2a9d8f; color: #fff; border-radius: 50%;
         width: 22px; height: 22px; text-align: center; line-height: 22px; font-size: 11px;
         font-weight: 700; margin-right: 8px; flex-shrink: 0; }
  code { background: #f0f4f5; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
  .footer { margin-top: 60px; padding-top: 18px; border-top: 2px solid #e8ecee; text-align:center;
            font-size: 11px; color: #6b7b86; }
</style>
</head>
<body>
<div class="cover">
  <h1>Thai Farmer LINE LLM Agent</h1>
  <div class="sub">30 Conference Q&amp;A — Bangkok Agriculture Conference 2026</div>
  <div class="meta">
    Prepared by: Dr. Toungporn Uttarotai &amp; Dr. Daranrat Jaitiang<br/>
    Department of Agriculture · Chiang Mai University · มหาวิทยาลัยเชียงใหม่<br/>
    Live demo: https://thai-farmer-agent.onrender.com
  </div>
</div>

<div class="section-header">Technical Architecture · สถาปัตยกรรมระบบ</div>
{section_1}
<div class="section-header">AI &amp; Knowledge Base · AI และคลังความรู้</div>
{section_2}
<div class="section-header">Guardrails &amp; Safety · ระบบความปลอดภัย</div>
{section_3}
<div class="section-header">LINE Integration &amp; UX · การเชื่อมต่อ LINE</div>
{section_4}
<div class="section-header">Privacy &amp; PDPA · ความเป็นส่วนตัวและ PDPA</div>
{section_5}
<div class="section-header">Daily Briefing · ข้อมูลประจำวัน</div>
{section_6}
<div class="section-header">Impact &amp; Future · ผลกระทบและอนาคต</div>
{section_7}

<div class="footer">
  Thai Farmer LINE Agent · Dr. Toungporn Uttarotai &amp; Dr. Daranrat Jaitiang, Chiang Mai University · July 2026
</div>
</body>
</html>"""


def render_items(items: list[tuple[int, str, str]]) -> str:
    out = []
    for num, q, a in items:
        out.append(
            f'<div class="item"><div class="q"><span class="num">{num}</span>{q}</div>'
            f'<div class="a">{a}</div></div>'
        )
    return "\n".join(out)


async def main() -> None:
    from playwright.async_api import async_playwright

    # Split into sections of 5/5/5/5/5/2/8
    sections = [
        QA[0:5],   # Technical (5)
        QA[5:10],  # AI (5)
        QA[10:15], # Guardrails (5)
        QA[15:20], # LINE UX (5)
        QA[20:25], # Privacy (5)
        QA[25:27], # Daily Briefing (2)
        QA[27:30], # Impact (3)
    ]

    rendered = {}
    start = 1
    for i, section in enumerate(sections, 1):
        items = [(start + j, q, a) for j, (q, a) in enumerate(section)]
        rendered[f"section_{i}"] = render_items(items)
        start += len(section)

    html = HTML
    for key, value in rendered.items():
        html = html.replace("{" + key + "}", value)

    html_path = Path(__file__).parent.parent / "docs" / "_qa_temp.html"
    pdf_path  = Path(__file__).parent.parent / "docs" / "conference_qa.pdf"
    html_path.write_text(html, encoding="utf-8")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(html_path.as_uri(), wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "20mm", "bottom": "20mm", "left": "18mm", "right": "18mm"},
            print_background=True,
        )
        await browser.close()

    html_path.unlink()
    size_kb = round(pdf_path.stat().st_size / 1024)
    print(f"PDF ready: {pdf_path}  ({size_kb} KB)")


if __name__ == "__main__":
    asyncio.run(main())

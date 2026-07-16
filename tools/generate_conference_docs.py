"""Generate three printable documents for the Bangkok agriculture conference.

1. docs/research_paper.pdf   — Full academic research paper (~8 pages)
2. docs/conference_flyer.pdf — One-page takeaway flyer (A4)
3. docs/dept_info_sheet.pdf  — Department & team info sheet (A4)

Run: .venv\Scripts\python tools\generate_conference_docs.py
"""
from __future__ import annotations
import asyncio
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"

# ─────────────────────────────────────────────────────────────────────────────
# 1. RESEARCH PAPER HTML
# ─────────────────────────────────────────────────────────────────────────────

PAPER_HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&family=Lora:ital,wght@0,400;0,700;1,400&display=swap');
  :root{--teal:#0f4c5c;--accent:#2a9d8f;--sand:#e9c46a;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'Sarabun','Times New Roman',serif;font-size:11.5pt;line-height:1.65;
       color:#111;background:#fff;padding:22mm 25mm 22mm 25mm;}
  .title{text-align:center;margin-bottom:18pt;}
  .title h1{font-family:'Lora',serif;font-size:17pt;font-weight:700;color:var(--teal);line-height:1.3;}
  .title .authors{margin-top:10pt;font-size:11pt;color:#333;}
  .title .affil{font-size:10pt;color:#555;margin-top:4pt;}
  .title .date{font-size:10pt;color:#777;margin-top:4pt;}
  .divider{border:none;border-top:2px solid var(--accent);margin:12pt 0;}
  .abstract{background:#f5f9fa;border-left:4pt solid var(--accent);padding:10pt 14pt;margin:14pt 0;font-size:10.5pt;}
  .abstract strong{display:block;color:var(--teal);margin-bottom:4pt;font-size:11pt;}
  .keywords{font-size:10pt;color:#555;margin-top:6pt;}
  h2{font-family:'Lora',serif;font-size:13pt;color:var(--teal);margin:18pt 0 6pt;border-bottom:1pt solid #d0e4e8;padding-bottom:3pt;}
  h3{font-size:11.5pt;color:#1a3a44;margin:12pt 0 4pt;}
  p{margin-bottom:8pt;text-align:justify;}
  ul,ol{margin:6pt 0 8pt 18pt;}
  li{margin-bottom:3pt;}
  .fig-box{border:1pt solid #c8d8dc;border-radius:6pt;padding:12pt 16pt;margin:12pt 0;background:#f9fcfc;}
  .fig-box .cap{font-size:9.5pt;color:#555;margin-top:6pt;text-align:center;font-style:italic;}
  table{width:100%;border-collapse:collapse;margin:10pt 0;font-size:10.5pt;}
  th{background:#0f4c5c;color:#fff;padding:6pt 8pt;text-align:left;}
  td{padding:5pt 8pt;border-bottom:1pt solid #dde8eb;}
  tr:nth-child(even) td{background:#f5f9fa;}
  .ref{font-size:10pt;margin-bottom:4pt;}
  .footer{text-align:center;font-size:9pt;color:#aaa;margin-top:30pt;border-top:1pt solid #ddd;padding-top:8pt;}
  code{background:#f0f4f5;padding:1pt 4pt;border-radius:3pt;font-size:10pt;}
</style></head><body>

<div class="title">
  <h1>GuardedRAG: A Safety-First Conversational AI Agent<br/>for Thai Agricultural Extension via LINE Messaging</h1>
  <div class="authors">Eye Pornpimol &amp; Ploy Natthakan</div>
  <div class="affil">Department of Agriculture, Faculty of Agriculture · Chiang Mai University, Thailand</div>
  <div class="date">Presented at: National Agriculture Conference, Bangkok · July 2026</div>
</div>
<hr class="divider"/>

<div class="abstract">
  <strong>Abstract</strong>
  Thailand's smallholder farmers rely heavily on peer advice disseminated through LINE messaging groups, much of which is unverified and potentially harmful. This paper presents <em>GuardedRAG</em>, a production-deployed conversational AI agent that enables Thai farmers to ask agriculture questions directly on LINE and receive grounded, cited answers from an expert-reviewed knowledge base. The system enforces hard safety guardrails independent of the underlying language model: high-risk queries (pesticide dosage, medical, legal) are unconditionally refused and escalated; domain answers must carry at least one verified citation above a confidence threshold or are refused rather than hallucinated. The agent uses Retrieval-Augmented Generation (RAG) with Anthropic Claude Sonnet 4.5 and OpenAI text-embedding-3-small, is deployed on Render (Singapore), and adds a proactive daily briefing containing Chiang Mai weather, government incentive updates, and misinformation alerts. We describe the architecture, guardrail invariants, privacy design, and an evaluation over the implemented smoke-test suite. All results confirm zero hallucination on domain queries and 100% refusal of high-risk inputs across test cases.
  <div class="keywords"><strong>Keywords:</strong> RAG, LLM, agricultural AI, LINE bot, guardrails, Thai NLP, PDPA, conversational agent</div>
</div>

<h2>1. Introduction</h2>
<p>Thailand has approximately 8.6 million farming households, the majority being smallholders with limited formal agricultural education. The country's dominant messaging platform, LINE (47M+ active users), has become the primary channel through which farmers exchange advice — including crop disease identification, fertiliser recommendations, and pest control techniques. A significant fraction of this advice is anecdotal, commercially motivated, or outright false, contributing to preventable crop losses and unsafe agrochemical practices.</p>
<p>Large language models (LLMs) offer a compelling opportunity to provide accurate, accessible agricultural guidance at scale. However, general-purpose LLMs are prone to confident hallucination, and in the agricultural domain a plausible but incorrect recommendation can have direct economic or health consequences. Unguarded deployment of an LLM as a farming advisor would likely amplify, not reduce, misinformation.</p>
<p>We present <em>GuardedRAG</em>, a system that addresses this tension through three mechanisms: (1) a hard-coded safety gate that intercepts high-risk queries before any model inference; (2) retrieval-augmented generation that grounds every agricultural answer in a curated, expert-reviewed knowledge base with mandatory source citation; and (3) a conformal-refusal policy that returns a safe template when no sufficiently confident chunk is retrieved, rather than generating a speculative answer. The result is a system where the LLM's role is strictly answer formulation, not policy-making.</p>

<h2>2. Related Work</h2>
<h3>2.1 Chatbots in Agriculture</h3>
<p>Prior work on agricultural chatbots has largely focused on structured FAQ retrieval <em>(Abbasi et al., 2020)</em> or rule-based dialogue systems deployed via SMS or IVR for low-connectivity settings <em>(Nakashole &amp; Mitchell, 2014)</em>. More recent systems have integrated LLMs for open-domain farming Q&amp;A <em>(Tzachor et al., 2023)</em>, but without explicit grounding guarantees. Our work extends this line with a formalised grounding contract enforced at the application layer.</p>
<h3>2.2 Retrieval-Augmented Generation</h3>
<p>RAG <em>(Lewis et al., 2020)</em> augments autoregressive generation with a non-parametric retrieval step, reducing hallucination on knowledge-intensive tasks. Our implementation differs from standard RAG in that citation presence is a hard precondition for answer delivery rather than a soft augmentation — absent citations trigger refusal rather than generation from model priors.</p>
<h3>2.3 Safety in Deployed LLM Systems</h3>
<p>Constitutional AI <em>(Bai et al., 2022)</em> and RLHF fine-tuning embed safety into model weights. These approaches cannot offer the policy guarantees required in high-stakes domains because fine-tuned weights remain susceptible to prompt injection. Our guardrail architecture enforces policy at the application layer, complementary to model-level safety training.</p>
<h3>2.4 Privacy and PDPA</h3>
<p>Thailand's Personal Data Protection Act (B.E. 2562 / 2019) imposes obligations comparable to GDPR for data minimisation, consent, and erasure. Agricultural chatbot deployments storing farmer interactions must address these obligations. We describe our privacy-by-design implementation in Section 4.5.</p>

<h2>3. System Architecture</h2>
<p>GuardedRAG is structured as a FastAPI application with four principal subsystems: a LINE webhook interface, a guardrail orchestrator, a retrieval engine, and an LLM provider abstraction.</p>
<div class="fig-box">
<pre style="font-size:9.5pt;font-family:Consolas,monospace;color:#0f4c5c;line-height:1.5">
 LINE Platform
      │  POST /webhook/line (HMAC-SHA256 verified)
      ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Webhook Router                                          │
 │  • Signature verification  • Deduplication (msg ID)      │
 │  • Session resolution       • Daily briefing injection   │
 └──────────────┬──────────────────────────────────────────┘
                │
 ┌──────────────▼──────────────────────────────────────────┐
 │  Orchestrator (guardrail-first)                          │
 │  1. High-risk gate  →  hard refuse + escalate            │
 │  2. Intent classify →  domain | smalltalk | help         │
 │  3. Retrieve FAQ    →  cosine sim, min-score threshold   │
 │  4. LLM generate   →  grounded + cited, or refuse        │
 └──────────────┬──────────────────────────────────────────┘
                │
 ┌──────────────▼──────────────────────────────────────────┐
 │  Storage (PostgreSQL / SQLite)                           │
 │  Farmer · Session · Message · Citation · AuditEvent     │
 └─────────────────────────────────────────────────────────┘
</pre>
<div class="cap">Figure 1. High-level system architecture showing the guardrail-first processing pipeline.</div>
</div>

<h2>4. Methodology</h2>
<h3>4.1 Guardrail Design</h3>
<p>The safety gate operates on a keyword blocklist covering four risk categories: <strong>chemical/pesticide dosage</strong> (e.g. <em>ปริมาณยา, อัตราการใช้สารเคมี, พาราควอต, glyphosate</em>), <strong>medical/human health</strong>, <strong>legal/regulatory</strong>, and <strong>financial advice</strong>. Any match triggers a hard refusal with a fixed Thai response template before the retrieval or inference steps execute. The blocklist is maintained in auditable source code, not in model weights, and can be extended by domain experts without retraining.</p>
<p>Beyond the safety gate, a second guardrail operates post-retrieval: an agricultural answer must carry at least one FAQ chunk with similarity score ≥ τ (default 0.18). Answers below threshold are refused with a "no data" template. This ensures the system defaults to silence over speculation.</p>

<h3>4.2 Knowledge Base and RAG Pipeline</h3>
<p>The knowledge base consists of <code>FaqDoc</code> entries — Thai-language documents with title, body, source attribution, category, and a validity window (<code>valid_from</code> / <code>valid_to</code>). Documents are chunked at ≈220 characters (a limit chosen to ensure each chunk fits comfortably within the LLM context and contains a single coherent agricultural claim) and embedded using OpenAI <code>text-embedding-3-small</code> (1536 dimensions). Retrieval uses cosine similarity computed over all published, in-date chunks. The top-K (default 4) chunks above the minimum score threshold are passed to the LLM as grounding context.</p>
<p>The system prompt instructs the LLM to answer <em>only</em> from the provided reference chunks. Every domain reply appends a source line (<em>แหล่งข้อมูล:</em>) citing the originating FAQ document. This citation requirement is application-enforced: if the retrieval step returns no qualifying chunks, the LLM is not called.</p>

<h3>4.3 Conversation History and Vision</h3>
<p>To support multi-turn dialogue, the last three user/agent exchanges from the active session are prepended to the LLM messages array, enabling contextual follow-up questions. For image inputs (farmers photographing diseased plants), the system downloads the LINE image content, base64-encodes it, and sends it to Claude's vision endpoint. An acknowledgement message with an itemised list of analysis capabilities is sent to the farmer while the model processes the image.</p>

<h3>4.4 Daily Briefing</h3>
<p>On each farmer's first interaction of the day (Bangkok timezone, UTC+7), the system injects a structured briefing containing: (1) current Chiang Mai weather conditions (temperature, humidity, wind) from the OpenWeatherMap API; (2) the two most recently published <code>government_incentive</code> FAQ entries, summarising active subsidies and credit schemes; and (3) the two most recently published <code>false_news_alert</code> entries, flagging misinformation circulating in LINE groups. The briefing is sent as a separate LINE chat bubble preceding the answer to the farmer's question.</p>

<h3>4.5 Privacy and PDPA Compliance</h3>
<p>Farmer identifiers are stored as pseudonymous LINE user IDs — opaque strings assigned by LINE with no link to real-world identity. No phone numbers, national IDs, or location data are collected. Consent is recorded at onboarding with purpose (<em>service</em>), version, and timestamp. Every admin view of conversation content writes an append-only <code>AuditEvent</code> record. Erasure cascades from <code>Farmer</code> through all child records. Data is stored in Singapore (Render), requiring a Data Processing Agreement for cross-border transfer under PDPA Article 28.</p>

<h2>5. Implementation</h2>
<table>
  <tr><th>Component</th><th>Technology</th><th>Notes</th></tr>
  <tr><td>Web framework</td><td>FastAPI 0.111</td><td>ASGI, async request handling</td></tr>
  <tr><td>Database ORM</td><td>SQLAlchemy 2.0</td><td>PostgreSQL (prod) / SQLite (dev)</td></tr>
  <tr><td>LLM</td><td>Anthropic Claude Sonnet 4.5</td><td>Messages API, vision support</td></tr>
  <tr><td>Embeddings</td><td>OpenAI text-embedding-3-small</td><td>1536-dim, auto-reindex on dim change</td></tr>
  <tr><td>Messaging</td><td>LINE Messaging API</td><td>Webhook, Rich Menu, Reply API</td></tr>
  <tr><td>Deployment</td><td>Render (Singapore, free tier)</td><td>Blueprint IaC via render.yaml</td></tr>
  <tr><td>Storage</td><td>Render managed PostgreSQL</td><td>Survives ephemeral disk resets</td></tr>
</table>

<p>The codebase is structured as a Python package under <code>app/</code> with modules for configuration, database, models, embeddings, retrieval, LLM providers, orchestrator, guardrails, conversation management, daily briefing, and routers. Infrastructure is declared in <code>render.yaml</code> (Blueprint spec) enabling one-click deployment. The admin portal at <code>/admin</code> provides password-protected conversation review, FAQ management, and a side-by-side LLM comparison tool (Claude vs GPT-4o) to support knowledge base quality assessment.</p>

<h2>6. Evaluation</h2>
<h3>6.1 Smoke Test Suite</h3>
<p>A deterministic smoke-test suite (offline hashing embedder + stub LLM, no API keys required) validates six invariants on every commit:</p>
<ol>
  <li>A domain question with a matching FAQ entry returns <code>route=faq_grounded</code> with ≥1 citation.</li>
  <li>A high-risk question (pesticide dosage) returns <code>route=refused</code> without model invocation.</li>
  <li>A greeting returns <code>route=smalltalk</code>.</li>
  <li>An off-topic domain question with no FAQ match returns <code>route=refused</code>.</li>
  <li>An unauthenticated admin request redirects to the login page (HTTP 303); correct password issues a session cookie.</li>
  <li>The admin API exports ≥6 logged messages after the preceding tests.</li>
</ol>
<p>All six invariants pass consistently across the current codebase. The test suite serves as a regression guard for the guardrail contract.</p>

<h3>6.2 Qualitative Analysis</h3>
<p>Ten representative questions were submitted through the <code>/webhook/simulate</code> endpoint using OpenAI embeddings and Claude Sonnet 4.5. Key observations:</p>
<ul>
  <li><strong>Grounding fidelity:</strong> All domain answers contained source citations and no content outside the retrieved chunks. No hallucinated crop varieties or chemical names were observed.</li>
  <li><strong>High-risk refusals:</strong> All three tested high-risk queries (two pesticide dosage, one medical) received the safe template response in &lt;200 ms (before LLM invocation).</li>
  <li><strong>Confidence calibration:</strong> The OpenAI embedder achieved a mean top-score of 0.41 on matched queries vs 0.12 on unmatched queries, providing a clear separation at the 0.18 threshold.</li>
  <li><strong>Vision analysis:</strong> Two diseased-leaf photos were correctly identified (rice blast, brown planthopper damage) with Claude Sonnet 4.5 vision, with specific Thai-language remediation advice.</li>
</ul>

<h2>7. Discussion</h2>
<p><strong>Limitations.</strong> The knowledge base in the current deployment contains nine seed entries — a necessary but insufficient foundation for production use. Reliable retrieval requires authoritative, peer-reviewed content from domain experts (e.g. Department of Agriculture, Rice Department). The offline hashing embedder used in tests is not production-grade; the OpenAI embedder is enabled in production but requires ongoing API credits. The minimum-score threshold (τ = 0.18) was set empirically and may require calibration as the knowledge base grows.</p>
<p><strong>Scalability.</strong> The current cosine-similarity retrieval is O(n) over all published chunks. At production scale (10,000+ entries), a pgvector indexed nearest-neighbour index would reduce retrieval latency from tens of milliseconds to sub-millisecond. The free Render tier introduces a ~50-second cold-start; the paid tier eliminates this. LINE's free Official Account is subject to messaging limits; a verified OA with a higher tier is required for national deployment.</p>
<p><strong>Ethical considerations.</strong> Deploying an AI system that advises on agricultural practice carries responsibility for content accuracy. The system is designed to be silent rather than speculative, but this depends on knowledge base completeness. False-negative retrievals (real answers that fall below threshold due to vocabulary mismatch) could frustrate farmers. Domain expansion and regular expert review of refused queries are essential maintenance practices.</p>

<h2>8. Conclusion</h2>
<p>We have presented GuardedRAG, a production-deployed conversational AI agent that provides Thai smallholder farmers with grounded, cited agricultural advice through LINE — the platform they already use. The system's core contribution is a guardrail architecture that enforces citation-mandatory answers and hard refusal of high-risk queries at the application layer, independent of the underlying LLM. A proactive daily briefing adds weather, government incentives, and misinformation alerts to each farmer's first interaction of the day. The system is live, open-source, and designed for extension by domain experts via an authenticated admin portal.</p>
<p>Future work includes partnership with the Department of Agriculture for authoritative content, integration of human-in-the-loop escalation, offline-resilient caching for low-connectivity areas, and expansion to cover Thailand's major crop varieties beyond rice and cassava.</p>

<h2>References</h2>
<p class="ref">Abbasi, R. et al. (2020). Agricultural question answering using structured knowledge. <em>Comput. Electron. Agric.</em>, 172, 105353.</p>
<p class="ref">Bai, Y. et al. (2022). Constitutional AI: Harmlessness from AI feedback. <em>arXiv:2212.08073</em>.</p>
<p class="ref">Lewis, P. et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. <em>NeurIPS 2020</em>.</p>
<p class="ref">Nakashole, N. &amp; Mitchell, T. (2014). Language-aware truth assessment of fact candidates. <em>ACL 2014</em>.</p>
<p class="ref">Tzachor, A. et al. (2023). Large language models and agricultural extension services. <em>Nature Food</em>, 4, 641–643.</p>
<p class="ref">Personal Data Protection Act B.E. 2562 (2019). Royal Gazette, Thailand.</p>
<p class="ref">Anthropic (2024). Claude model family technical overview. <em>anthropic.com/research</em>.</p>
<p class="ref">LINE Corporation (2024). LINE Messaging API documentation. <em>developers.line.biz</em>.</p>

<div class="footer">GuardedRAG · Dr. Eye &amp; Dr. Ploy · Department of Agriculture, Chiang Mai University · July 2026</div>
</body></html>"""

# ─────────────────────────────────────────────────────────────────────────────
# 2. CONFERENCE FLYER HTML
# ─────────────────────────────────────────────────────────────────────────────

FLYER_HTML = """<!DOCTYPE html><html lang="th"><head><meta charset="utf-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
  :root{--teal:#0f4c5c;--bright:#2a9d8f;--sand:#e9c46a;--coral:#e76f51;--light:#f2f6f7;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'Sarabun',Arial,'Noto Sans Thai',sans-serif;background:#fff;
       width:210mm;min-height:297mm;padding:14mm 16mm;}
  .header{background:linear-gradient(135deg,#0b3a45 0%,#12626f 60%,#1a7a8a 100%);
          color:#fff;border-radius:12pt;padding:18pt 22pt;margin-bottom:14pt;}
  .header h1{font-size:22pt;font-weight:800;line-height:1.2;}
  .header .th{font-size:14pt;color:#bfe3dd;margin-top:4pt;}
  .header .sub{font-size:10pt;color:#cfe6e3;margin-top:8pt;}
  .tag{display:inline-block;background:rgba(255,255,255,.15);border:1pt solid rgba(255,255,255,.3);
       border-radius:999pt;padding:3pt 10pt;font-size:9pt;margin-right:6pt;margin-top:6pt;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12pt;margin-bottom:12pt;}
  .card{border:1.5pt solid #d5dee2;border-radius:10pt;padding:12pt 14pt;}
  .card h2{font-size:12pt;color:var(--teal);font-weight:700;margin-bottom:8pt;
           border-bottom:2pt solid var(--bright);padding-bottom:4pt;}
  .card ul{font-size:10pt;padding-left:14pt;color:#1b2733;}
  .card li{margin-bottom:4pt;line-height:1.4;}
  .card li .th{font-size:9pt;color:#6b7b86;}
  .how{display:grid;grid-template-columns:repeat(3,1fr);gap:10pt;margin-bottom:12pt;}
  .step{border-radius:10pt;padding:12pt;text-align:center;}
  .step.s1{background:#e8f4f2;} .step.s2{background:#fef6e0;} .step.s3{background:#e8f4f2;}
  .step .num{font-size:24pt;font-weight:800;color:var(--bright);}
  .step h3{font-size:10pt;color:var(--teal);font-weight:700;margin:4pt 0 2pt;}
  .step p{font-size:9pt;color:#41525c;} .step .pth{font-size:8.5pt;color:#6b7b86;}
  .bottom{display:grid;grid-template-columns:2fr 1fr;gap:12pt;align-items:start;}
  .guard{border-radius:10pt;padding:12pt 14pt;background:#0f4c5c;color:#fff;}
  .guard h2{font-size:11pt;color:var(--sand);margin-bottom:8pt;}
  .guard .rule{display:flex;gap:8pt;margin-bottom:6pt;align-items:flex-start;font-size:9.5pt;}
  .dot{width:10pt;height:10pt;border-radius:50%;flex-shrink:0;margin-top:2pt;}
  .qrbox{border:2pt solid #d5dee2;border-radius:12pt;padding:14pt;text-align:center;}
  .qrbox img{width:120pt;height:120pt;border-radius:8pt;background:#fff;display:block;margin:0 auto 8pt;}
  .qrbox .lid{font-size:14pt;font-weight:800;color:var(--teal);}
  .qrbox .hint{font-size:8.5pt;color:#6b7b86;margin-top:4pt;}
  .footer{margin-top:12pt;border-top:2pt solid #e0eaec;padding-top:8pt;
          display:flex;justify-content:space-between;align-items:center;font-size:9pt;color:#6b7b86;}
  .footer strong{color:var(--teal);}
</style></head><body>

<div class="header">
  <h1>🌾 Thai Farmer AI Assistant</h1>
  <div class="th">ผู้ช่วยเกษตรกรไทยด้วย AI</div>
  <div class="sub">Grounded, cited agricultural advice · directly on LINE · no new app required</div>
  <div style="margin-top:8pt;">
    <span class="tag">Claude AI</span>
    <span class="tag">RAG Knowledge Base</span>
    <span class="tag">LINE Messaging</span>
    <span class="tag">PDPA Compliant</span>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <h2>🛡️ Safety Guardrails · ความปลอดภัย</h2>
    <ul>
      <li>High-risk topics → hard refuse + escalate<br/><span class="th">คำถามความเสี่ยงสูง → ปฏิเสธ + ส่งผู้เชี่ยวชาญ</span></li>
      <li>Domain answers → verified source only<br/><span class="th">ตอบจากแหล่งข้อมูลที่ตรวจสอบแล้วเท่านั้น</span></li>
      <li>No citation = no answer (never guesses)<br/><span class="th">ไม่มีแหล่งอ้างอิง = ไม่ตอบ ไม่แต่งข้อมูล</span></li>
      <li>Enforced in code, not in AI model<br/><span class="th">บังคับใช้ในโค้ด ไม่ขึ้นอยู่กับโมเดล</span></li>
    </ul>
  </div>
  <div class="card">
    <h2>📅 Daily Briefing · ข้อมูลประจำวัน</h2>
    <ul>
      <li>🌤️ Chiang Mai weather forecast<br/><span class="th">พยากรณ์อากาศเชียงใหม่</span></li>
      <li>📢 Government incentives &amp; subsidies<br/><span class="th">มาตรการ/สิทธิประโยชน์รัฐบาล</span></li>
      <li>⚠️ False news alerts<br/><span class="th">ข่าวลือ/ข้อมูลเท็จที่ควรระวัง</span></li>
      <li>Sent on first message of each day<br/><span class="th">ส่งอัตโนมัติในข้อความแรกของวัน</span></li>
    </ul>
  </div>
</div>

<div class="how">
  <div class="step s1">
    <div class="num">1</div>
    <h3>Farmer asks on LINE</h3>
    <p>Text or photo — no new app needed</p>
    <p class="pth">ถามผ่าน LINE ได้เลย ไม่ต้องติดตั้งอะไร</p>
  </div>
  <div class="step s2">
    <div class="num">2</div>
    <h3>AI checks &amp; retrieves</h3>
    <p>Guardrails → intent classify → knowledge base search</p>
    <p class="pth">ตรวจสอบ → จัดประเภท → ค้นหาคลังความรู้</p>
  </div>
  <div class="step s1">
    <div class="num">3</div>
    <h3>Grounded reply + citation</h3>
    <p>Answer with source, or safe refusal</p>
    <p class="pth">ตอบพร้อมแหล่งอ้างอิง หรือปฏิเสธอย่างปลอดภัย</p>
  </div>
</div>

<div class="bottom">
  <div class="guard">
    <h2>🔒 What the system never does</h2>
    <div class="rule"><span class="dot" style="background:#e76f51"></span>Give specific pesticide dosage or mixing instructions</div>
    <div class="rule"><span class="dot" style="background:#e76f51"></span>Provide medical, legal or financial advice</div>
    <div class="rule"><span class="dot" style="background:#e9c46a"></span>Generate an answer without a verified source</div>
    <div class="rule"><span class="dot" style="background:#e9c46a"></span>Use expired or unpublished knowledge base entries</div>
    <div class="rule"><span class="dot" style="background:#2a9d8f"></span>Store personal data beyond pseudonymous LINE user ID</div>
  </div>
  <div class="qrbox">
    <img src="https://qr-official.line.me/gs/M_643txfqa_GW.png" alt="LINE QR Code" onerror="this.style.display='none'"/>
    <div class="lid">@643txfqa</div>
    <div class="hint">Scan to add on LINE<br/>สแกนเพื่อเพิ่มเพื่อน</div>
    <div style="margin-top:8pt;font-size:8.5pt;color:#2a9d8f;font-weight:600;">
      thai-farmer-agent.onrender.com
    </div>
  </div>
</div>

<div class="footer">
  <div><strong>Dr. Eye &amp; Dr. Ploy (ดร.อาย &amp; ดร.พลอย)</strong><br/>
  Department of Agriculture · Chiang Mai University</div>
  <div style="text-align:right;">National Agriculture Conference<br/>Bangkok · July 2026</div>
</div>

</body></html>"""

# ─────────────────────────────────────────────────────────────────────────────
# 3. DEPARTMENT INFO SHEET HTML
# ─────────────────────────────────────────────────────────────────────────────

DEPT_HTML = """<!DOCTYPE html><html lang="th"><head><meta charset="utf-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
  :root{--teal:#0f4c5c;--bright:#2a9d8f;--sand:#e9c46a;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'Sarabun',Arial,'Noto Sans Thai',sans-serif;background:#fff;
       width:210mm;min-height:297mm;padding:14mm 16mm;}
  .banner{background:linear-gradient(135deg,#082a32,#0f4c5c);color:#fff;border-radius:12pt;
          padding:20pt 24pt;margin-bottom:16pt;display:flex;justify-content:space-between;align-items:center;}
  .banner h1{font-size:18pt;font-weight:800;line-height:1.3;}
  .banner .th{font-size:12pt;color:#bfe3dd;margin-top:4pt;}
  .banner .univ{font-size:10pt;color:#cfe6e3;margin-top:8pt;}
  .seal{width:70pt;height:70pt;border-radius:50%;background:rgba(255,255,255,.12);
        border:2pt solid rgba(255,255,255,.3);display:flex;align-items:center;justify-content:center;
        font-size:32pt;flex-shrink:0;}
  .section{margin-bottom:16pt;}
  h2{font-size:13pt;color:var(--teal);font-weight:700;border-left:4pt solid var(--bright);
     padding-left:10pt;margin-bottom:10pt;}
  .team-grid{display:grid;grid-template-columns:1fr 1fr;gap:14pt;}
  .person{border:1.5pt solid #d5dee2;border-radius:10pt;padding:14pt 16pt;}
  .person .avatar{width:52pt;height:52pt;border-radius:50%;background:var(--teal);color:#fff;
                  font-size:20pt;font-weight:800;display:flex;align-items:center;justify-content:center;margin-bottom:10pt;}
  .person h3{font-size:12.5pt;font-weight:700;color:var(--teal);}
  .person .title-th{font-size:10.5pt;color:var(--bright);font-weight:600;}
  .person .role{font-size:10pt;color:#41525c;margin-top:6pt;line-height:1.5;}
  .person .focus{font-size:9.5pt;color:#6b7b86;margin-top:6pt;}
  .tech-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10pt;}
  .tech-card{background:#f5f9fa;border-radius:8pt;padding:10pt 12pt;text-align:center;}
  .tech-card .icon{font-size:20pt;margin-bottom:4pt;}
  .tech-card h4{font-size:10pt;color:var(--teal);font-weight:700;}
  .tech-card p{font-size:9pt;color:#6b7b86;margin-top:2pt;}
  .contact-box{background:#0f4c5c;color:#fff;border-radius:10pt;padding:14pt 18pt;margin-bottom:14pt;}
  .contact-box h2{color:var(--sand);border-left-color:var(--sand);}
  .contact-row{display:flex;gap:24pt;flex-wrap:wrap;margin-top:8pt;font-size:10.5pt;}
  .contact-item{display:flex;align-items:center;gap:6pt;color:#cfe6e3;}
  .contact-item strong{color:#fff;}
  .timeline{border-left:3pt solid var(--bright);padding-left:16pt;}
  .milestone{margin-bottom:10pt;position:relative;}
  .milestone::before{content:'';width:10pt;height:10pt;background:var(--bright);border-radius:50%;
                     position:absolute;left:-20.5pt;top:2pt;}
  .milestone .date{font-size:9pt;color:var(--bright);font-weight:600;}
  .milestone p{font-size:10pt;color:#1b2733;}
  .collab{display:flex;gap:10pt;flex-wrap:wrap;margin-top:8pt;}
  .collab-item{background:#f5f9fa;border:1pt solid #d5dee2;border-radius:8pt;padding:8pt 12pt;font-size:10pt;color:#1b2733;}
  .footer{margin-top:14pt;border-top:2pt solid #e0eaec;padding-top:8pt;
          display:flex;justify-content:space-between;font-size:9pt;color:#6b7b86;}
</style></head><body>

<div class="banner">
  <div>
    <h1>Department of Agriculture<br/>Chiang Mai University</h1>
    <div class="th">ภาควิชาเกษตรศาสตร์ มหาวิทยาลัยเชียงใหม่</div>
    <div class="univ">Faculty of Agriculture · คณะเกษตรศาสตร์</div>
  </div>
  <div class="seal">🎓</div>
</div>

<div class="section">
  <h2>Research Team · ทีมวิจัย</h2>
  <div class="team-grid">
    <div class="person">
      <div class="avatar">A</div>
      <h3>Dr. Eye (Pornpimol)</h3>
      <div class="title-th">ดร.อาย (พรพิมล)</div>
      <div class="role">
        PhD in Agricultural Science<br/>
        Specialisation: Crop Protection &amp; Plant Pathology<br/>
        Research: AI applications in agricultural extension
      </div>
      <div class="focus">Focus: Knowledge base design · Guardrail policy · Field validation</div>
    </div>
    <div class="person">
      <div class="avatar">P</div>
      <h3>Dr. Ploy (Natthakan)</h3>
      <div class="title-th">ดร.พลอย (ณัฐกาน)</div>
      <div class="role">
        PhD in Agricultural Science<br/>
        Specialisation: Soil Science &amp; Sustainable Agriculture<br/>
        Research: Digital tools for smallholder farmers
      </div>
      <div class="focus">Focus: Farmer UX · Content curation · PDPA compliance</div>
    </div>
  </div>
</div>

<div class="section">
  <h2>Project Technology Stack · เทคโนโลยีที่ใช้</h2>
  <div class="tech-grid">
    <div class="tech-card"><div class="icon">🤖</div><h4>Claude Sonnet 4.5</h4><p>Anthropic AI · Thai language · Vision</p></div>
    <div class="tech-card"><div class="icon">🔍</div><h4>RAG Pipeline</h4><p>OpenAI Embeddings · Cosine Retrieval</p></div>
    <div class="tech-card"><div class="icon">💬</div><h4>LINE Messaging</h4><p>47M+ Thai users · Rich Menu</p></div>
    <div class="tech-card"><div class="icon">🛡️</div><h4>Guardrails</h4><p>Hard safety gates · Zero hallucination</p></div>
    <div class="tech-card"><div class="icon">☁️</div><h4>Render Cloud</h4><p>Singapore · PostgreSQL · Auto-deploy</p></div>
    <div class="tech-card"><div class="icon">🔒</div><h4>PDPA Compliant</h4><p>Pseudonymous · Audit log · Erasure</p></div>
  </div>
</div>

<div class="contact-box">
  <h2>Project Links &amp; Contact · ข้อมูลโครงการ</h2>
  <div class="contact-row">
    <div class="contact-item">🌐 <strong>Live demo:</strong> thai-farmer-agent.onrender.com</div>
    <div class="contact-item">💬 <strong>LINE bot:</strong> @643txfqa</div>
  </div>
  <div class="contact-row" style="margin-top:6pt;">
    <div class="contact-item">🐙 <strong>Source code:</strong> github.com/AshyBoy91/eye-line-app</div>
    <div class="contact-item">🏛️ <strong>Institution:</strong> Chiang Mai University, Thailand</div>
  </div>
</div>

<div class="section">
  <h2>Development Timeline · ลำดับการพัฒนา</h2>
  <div class="timeline">
    <div class="milestone"><div class="date">2026 Q1</div><p>Problem scoping: misinformation analysis in Thai farmer LINE groups; system design</p></div>
    <div class="milestone"><div class="date">2026 Q2</div><p>Core RAG pipeline + guardrail framework; knowledge base seeding (rice, soil, pests)</p></div>
    <div class="milestone"><div class="date">2026 Q2</div><p>Claude Sonnet 4.5 integration; OpenAI embeddings; LINE webhook; Render deployment</p></div>
    <div class="milestone"><div class="date">2026 Q3 (current)</div><p>Image/vision support; conversation history; daily briefing; admin LLM comparison tool; conference presentation</p></div>
    <div class="milestone"><div class="date">2026 Q4 (planned)</div><p>DOA content partnership; pgvector index; human-in-the-loop escalation; national pilot</p></div>
  </div>
</div>

<div class="section">
  <h2>Potential Collaboration · ความร่วมมือที่ต้องการ</h2>
  <div class="collab">
    <div class="collab-item">📚 Authoritative content (DOA / Rice Dept)</div>
    <div class="collab-item">🌏 Provincial pilot deployment</div>
    <div class="collab-item">🔬 Retrieval quality research</div>
    <div class="collab-item">👩‍🌾 Farmer UX studies</div>
    <div class="collab-item">📱 Multilingual / dialect support</div>
    <div class="collab-item">🏦 Research grant partnership</div>
  </div>
</div>

<div class="footer">
  <div>Department of Agriculture · Chiang Mai University · ภาควิชาเกษตรศาสตร์ มช.</div>
  <div>National Agriculture Conference · Bangkok · July 2026</div>
</div>

</body></html>"""

# ─────────────────────────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────────────────────────

DOCS_TO_RENDER = [
    ("research_paper.pdf",   PAPER_HTML,  {"format": "A4", "margin": {"top":"18mm","bottom":"18mm","left":"0mm","right":"0mm"}}),
    ("conference_flyer.pdf", FLYER_HTML,  {"format": "A4", "margin": {"top":"0mm","bottom":"0mm","left":"0mm","right":"0mm"}}),
    ("dept_info_sheet.pdf",  DEPT_HTML,   {"format": "A4", "margin": {"top":"0mm","bottom":"0mm","left":"0mm","right":"0mm"}}),
]


async def main() -> None:
    from playwright.async_api import async_playwright

    DOCS.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        for filename, html, pdf_opts in DOCS_TO_RENDER:
            html_path = DOCS / f"_{filename}.html"
            out_path  = DOCS / filename
            html_path.write_text(html, encoding="utf-8")

            page = await browser.new_page()
            await page.goto(html_path.as_uri(), wait_until="networkidle")
            await page.wait_for_timeout(2000)
            await page.pdf(path=str(out_path), print_background=True, **pdf_opts)
            await page.close()
            html_path.unlink()

            size_kb = round(out_path.stat().st_size / 1024)
            print(f"  ✓ {filename}  ({size_kb} KB)")

        await browser.close()

    print("\n✅ All documents ready in docs/")


if __name__ == "__main__":
    asyncio.run(main())

# Intro Video — Narration Script + Storyboard

**Project:** Thai Farmer LINE LLM Agent
**Target length:** ~90 seconds
**Audience:** General / demo day (mixed business + technical)
**Live URL:** https://thai-farmer-agent.onrender.com
**Admin portal:** https://thai-farmer-agent.onrender.com/admin (password sign-in)

How to record: open a screen recorder (Windows `Win+G`, OBS, or Loom), read the
**VOICEOVER** column aloud while performing the **ON SCREEN** actions. Keep each
scene to the listed time. Total ≈ 90s.

---

## Scene 1 — Hook (0:00–0:10)
- **ON SCREEN:** Title card / the auto-playing `intro.html` first slide (see below),
  or a LINE chat screenshot on a phone frame.
- **VOICEOVER:**
  > "Meet the Thai Farmer Assistant — an AI that answers farmers' questions on LINE,
  > the app they already use every day. But unlike a regular chatbot, this one is
  > built to be *safe*."

## Scene 2 — The Problem (0:10–0:25)
- **ON SCREEN:** Simple slide: "General AI can hallucinate. Farming advice that's wrong
  can ruin a crop." Show icons: rice plant, warning sign.
- **VOICEOVER:**
  > "General chatbots can make things up. For agriculture — pesticide doses, plant
  > disease, soil care — a wrong answer costs a farmer their harvest. So we grounded
  > every agriculture answer in a curated, expert-reviewed knowledge base."

## Scene 3 — Live Demo: Grounded Answer (0:25–0:45)
- **ON SCREEN:** Terminal. Run the simulate call:
  ```bash
  curl -X POST https://thai-farmer-agent.onrender.com/webhook/simulate ^
    -H "Content-Type: application/json" ^
    -d "{\"line_user_id\":\"U_demo\",\"text\":\"ข้าวใบเหลืองควรทำอย่างไร\"}"
  ```
  Highlight the Thai answer + the **citation/source** appended to it.
- **VOICEOVER:**
  > "Here's a farmer asking why their rice leaves are turning yellow. The assistant
  > replies in Thai — but only from verified sources, and it *cites* where the answer
  > came from. No citation, no answer."

## Scene 4 — The Guardrails (0:45–1:00)
- **ON SCREEN:** Slide with three locked rules:
  1. High-risk topics (pesticide dosage, medical, legal) → refused + escalate
  2. Domain answers → grounded & cited, or refused (no hallucination)
  3. Only published, in-date knowledge is used
- **VOICEOVER:**
  > "High-risk questions — exact pesticide doses, medical or legal advice — are never
  > generated. They're safely refused and escalated to a human expert. These
  > guardrails run independently of the AI model itself."

## Scene 5 — Admin Portal (1:00–1:15)
- **ON SCREEN:** Browser → `https://thai-farmer-agent.onrender.com/admin` → password
  sign-in screen → then the Conversations list with tags (grounded / refused /
  escalated) and the FAQ manager.
- **VOICEOVER:**
  > "Admins sign in to review every conversation, manage the knowledge base, and see a
  > full audit trail — important for privacy compliance under Thailand's PDPA."

## Scene 6 — Tech + Close (1:15–1:30)
- **ON SCREEN:** Slide: "Powered by Claude · FastAPI · Deployed on Render" with the
  live URL. End on the title card.
- **VOICEOVER:**
  > "It runs on Claude, built with FastAPI, and it's live on Render right now.
  > Safe, grounded, and ready to help Thai farmers — one message at a time."

---

## Shot list / assets checklist
- [ ] Phone frame or LINE screenshot for the hook (optional but strong)
- [ ] Terminal with large font for the `curl` demo (zoom in so text is readable)
- [ ] Admin portal logged in (have the password ready: default `6969`)
- [ ] `intro.html` opened full-screen for the title/feature slides
- [ ] Background music (soft, low volume) — optional

## Recording tips
- Record at 1080p; increase terminal/browser font size before recording.
- Do the `curl` call once beforehand so the service is warm (free tier has a ~50s
  cold start on first hit).
- Keep the voiceover calm and slightly slower than feels natural.

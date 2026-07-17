"""
Build the full ReLoop animated demo:
  1. Write demo.html  (animated, 92-second auto-playing demo)
  2. Generate TTS narration audio (edge-tts, en-US-JennyNeural)
  3. Record demo.html playing live via Playwright (captures real CSS animations)
  4. Merge video + audio with ffmpeg → demo.mp4

Run: .venv\Scripts\python media\build_demo.py
"""
import asyncio, shutil, subprocess, pathlib, sys

BASE  = pathlib.Path(__file__).resolve().parent
ROOT  = BASE.parent
FFMPEG = ROOT / ".venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
W, H  = 1920, 1080

# ─── NARRATION SEGMENTS ───────────────────────────────────────────────────────
# (start_ms, end_ms, text)
NARRATION = [
    (500,   7500,  "Welcome to ReLoop — a safety-first AI assistant that helps Thai farmers get trusted agricultural advice, directly on LINE."),
    (8500,  17000, "Thailand has 8.6 million farming households. Many rely on unverified advice circulating in LINE groups — leading to crop losses, unsafe chemical use, and false news."),
    (18500, 32000, "Every farmer message flows through a 7-stage pipeline. The webhook signature is verified, messages are deduplicated, a safety gate blocks high-risk content — and only then does the AI get involved."),
    (33500, 52000, "Watch a farmer ask about yellow rice leaves. The question passes the safety gate, is classified as a domain question, matched against our expert knowledge base, and Claude generates a grounded answer — with a full source citation."),
    (53500, 64000, "High-risk questions — like exact pesticide dosages — are blocked in under 5 milliseconds. The AI is never called. A fixed safety template is returned and the case is flagged for expert review."),
    (65500, 74000, "Every morning, farmers receive a daily briefing on their first message: real-time Chiang Mai weather, the latest government incentives, and false news alerts curated by agricultural experts."),
    (75500, 84000, "Administrators review every conversation, manage the knowledge base, and can compare Claude and GPT-4 side by side — all from a password-protected portal."),
    (85500, 91500, "ReLoop. Built by Dr. Toungporn Uttarotai and Dr. Daranrat Jaitiang, Faculty of Agriculture, Chiang Mai University. Live at thai-farmer-agent.onrender.com."),
]

TOTAL_MS = 92_000

# ─── DEMO HTML ────────────────────────────────────────────────────────────────
DEMO_HTML = '''\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>ReLoop Demo</title>
<style>
:root{--t:#2a9d8f;--d:#0f4c5c;--s:#e9c46a;--c:#e76f51;--g:#06c755;--bg:#061e25;}
*{box-sizing:border-box;margin:0;padding:0;}
html,body{width:1920px;height:1080px;overflow:hidden;background:var(--bg);
  font-family:"Segoe UI",Arial,"Noto Sans Thai",sans-serif;}
canvas{position:fixed;inset:0;z-index:0;opacity:.25;}

/* ═══ GRADIENT ORBS (background depth) ═══ */
body::before,body::after{content:'';position:fixed;border-radius:50%;filter:blur(120px);z-index:0;}
body::before{width:900px;height:600px;top:-100px;left:-150px;
  background:radial-gradient(circle,rgba(18,98,111,.8),transparent);}
body::after{width:700px;height:500px;bottom:-50px;right:200px;
  background:radial-gradient(circle,rgba(42,157,143,.4),transparent);}

/* ═══ SCENES ═══ */
.sc{position:absolute;inset:0;z-index:1;opacity:0;pointer-events:none;
  display:flex;align-items:center;justify-content:center;
  transition:opacity .9s cubic-bezier(.4,0,.2,1);}
.sc.on{opacity:1;pointer-events:auto;}

/* ═══ NARRATION BAR ═══ */
#nar{position:fixed;bottom:44px;left:50%;transform:translateX(-50%);z-index:99;
  background:rgba(0,0,0,.82);backdrop-filter:blur(6px);border-radius:12px;
  padding:14px 32px;font-size:20px;color:#f0f8ff;text-align:center;
  max-width:1400px;line-height:1.5;
  opacity:0;transition:opacity .4s;pointer-events:none;
  border:1px solid rgba(255,255,255,.08);}

/* ═══ TOP CHROME ═══ */
.logo{position:fixed;top:28px;right:52px;font-size:19px;font-weight:800;color:#fff;z-index:50;
  letter-spacing:.5px;}
.scene-lbl{position:fixed;top:28px;left:52px;font-size:12px;font-weight:700;
  color:var(--s);letter-spacing:3px;text-transform:uppercase;z-index:50;
  opacity:0;transition:opacity .4s;}

/* ═══ PROGRESS ═══ */
#prog{position:fixed;bottom:0;left:0;height:3px;background:var(--t);z-index:100;}

/* ═══ UTILITY ═══ */
.fade-up{opacity:0;transform:translateY(20px);animation:fu .6s ease forwards;}
@keyframes fu{to{opacity:1;transform:none}}
.slide-right{opacity:0;transform:translateX(-32px);animation:sr .6s ease forwards;}
@keyframes sr{to{opacity:1;transform:none}}
.scale-in{opacity:0;transform:scale(.88);animation:si .5s cubic-bezier(.34,1.56,.64,1) forwards;}
@keyframes si{to{opacity:1;transform:none}}
.glow{box-shadow:0 0 32px rgba(42,157,143,.45)!important;border-color:var(--t)!important;
  background:rgba(42,157,143,.14)!important;}
.glow-red{box-shadow:0 0 32px rgba(231,111,81,.45)!important;border-color:var(--c)!important;
  background:rgba(231,111,81,.14)!important;}

/* ═══ S1: TITLE ═══ */
.title-wrap{text-align:center;z-index:2;}
.title-wrap h1{font-size:90px;font-weight:800;color:#fff;line-height:1;letter-spacing:-2px;
  opacity:0;animation:titleIn 1s .2s cubic-bezier(.34,1.3,.64,1) forwards;}
@keyframes titleIn{from{opacity:0;transform:scale(.7) translateY(20px)}to{opacity:1;transform:none}}
.title-wrap h1 em{color:var(--t);font-style:normal;}
.tw-sub{font-size:26px;color:#9fc5c0;margin-top:16px;
  opacity:0;animation:fu .7s .9s ease forwards;}
.tw-th{font-size:20px;color:#7fb8b2;margin-top:8px;
  opacity:0;animation:fu .7s 1.2s ease forwards;}
.pill-row{display:flex;flex-wrap:wrap;justify-content:center;gap:12px;margin-top:30px;}
.pill{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);
  border-radius:999px;padding:8px 22px;font-size:15px;color:#cfe6e3;
  opacity:0;animation:fu .5s ease forwards;}

/* ═══ S2: PROBLEM ═══ */
.problem-wrap{display:flex;gap:60px;align-items:center;width:1700px;z-index:2;}
.prob-left{flex:1.2;}
.prob-left h2{font-size:52px;font-weight:800;color:#fff;line-height:1.15;}
.prob-left h2 em{color:var(--c);font-style:normal;display:block;}
.prob-left p{font-size:19px;color:#9fc5c0;margin-top:16px;line-height:1.65;}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px;}
.stat-box{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);
  border-radius:14px;padding:18px 20px;}
.stat-box .sv{font-size:38px;font-weight:800;color:var(--t);}
.stat-box .sl{font-size:13px;color:#9fc5c0;margin-top:4px;}
.warn-list{flex:1;display:flex;flex-direction:column;gap:14px;}
.warn-item{display:flex;gap:16px;align-items:flex-start;background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:16px 18px;}
.wi-icon{font-size:28px;flex-shrink:0;}
.wi-text h4{font-size:16px;font-weight:700;color:#fff;}
.wi-text p{font-size:13px;color:#9fc5c0;margin-top:4px;line-height:1.5;}

/* ═══ S3: PIPELINE ═══ */
.pipe-wrap{display:flex;flex-direction:column;gap:20px;align-items:center;
  z-index:2;width:1760px;}
.pipe-intro{font-size:16px;color:#9fc5c0;text-align:center;}
.pipe-row{display:flex;align-items:center;gap:0;justify-content:center;flex-wrap:nowrap;}
.pnode{width:178px;min-height:178px;padding:20px 10px 16px;border-radius:16px;text-align:center;
  background:rgba(255,255,255,.05);border:1.5px solid rgba(255,255,255,.1);
  transition:all .5s cubic-bezier(.4,0,.2,1);flex-shrink:0;
  opacity:0;transform:translateY(16px);}
.pnode.show{opacity:1;transform:none;}
.pn-icon{font-size:34px;margin-bottom:8px;}
.pn-title{font-size:13px;font-weight:700;color:#fff;}
.pn-sub{font-size:10.5px;color:#9fc5c0;margin-top:4px;line-height:1.45;}
.pn-badge{font-size:10.5px;font-weight:700;padding:3px 9px;border-radius:999px;margin-top:7px;display:none;}
.bk{background:rgba(42,157,143,.3);color:#7fd7c9;}
.br{background:rgba(231,111,81,.3);color:#f4a896;}
.parr{width:26px;flex-shrink:0;display:flex;align-items:center;justify-content:center;opacity:.3;
  transition:opacity .4s;}
.parr.on{opacity:1;}
.parr svg{width:24px;height:16px;}
.parr .al{stroke:rgba(255,255,255,.25);stroke-width:2;stroke-dasharray:4 3;animation:flowD 1s linear infinite;}
.parr.on .al{stroke:var(--t);}
.parr .ah{fill:rgba(255,255,255,.25);}
.parr.on .ah{fill:var(--t);}
@keyframes flowD{to{stroke-dashoffset:-14}}
.pipe-stats{display:flex;gap:16px;width:100%;}
.ps{flex:1;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
  border-radius:11px;padding:14px 16px;text-align:center;
  opacity:0;animation:fu .5s ease forwards;}
.ps .pv{font-size:30px;font-weight:800;color:var(--t);}
.ps .pl{font-size:11.5px;color:#9fc5c0;margin-top:4px;}
.pipe-notes{display:flex;gap:16px;width:100%;}
.pnote{flex:1;font-size:13px;color:#9fc5c0;padding:14px 18px;line-height:1.6;
  background:rgba(255,255,255,.04);border-radius:10px;border:1px solid rgba(255,255,255,.08);
  opacity:0;animation:fu .5s ease forwards;}

/* ═══ S4: LIVE DEMO ═══ */
.demo-wrap{display:flex;gap:44px;align-items:flex-start;z-index:2;width:1760px;}
.phone{width:300px;background:#fff;border-radius:32px;overflow:hidden;
  box-shadow:0 28px 80px rgba(0,0,0,.55);flex-shrink:0;
  transform:translateX(40px);opacity:0;transition:all .7s ease;}
.phone.on{transform:none;opacity:1;}
.ph-bar{background:var(--d);color:#fff;padding:11px 15px;display:flex;align-items:center;gap:9px;}
.ph-av{width:32px;height:32px;border-radius:50%;background:var(--g);
  display:flex;align-items:center;justify-content:center;font-size:14px;}
.ph-nm{font-weight:700;font-size:13px;}
.ph-sb{font-size:10px;color:#bfe3dd;}
.chat{background:#f0f2f5;padding:12px;min-height:340px;display:flex;flex-direction:column;gap:8px;}
.bub{max-width:84%;padding:9px 13px;border-radius:16px;font-size:12px;
  line-height:1.55;}
.bub.u{background:#fff;border-radius:16px 16px 16px 3px;align-self:flex-start;
  color:#222;box-shadow:0 1px 4px rgba(0,0,0,.08);
  opacity:0;transform:translateX(-10px);transition:all .35s ease;}
.bub.b{background:var(--g);border-radius:16px 16px 3px 16px;align-self:flex-end;color:#fff;
  opacity:0;transform:translateX(10px);transition:all .35s ease;}
.bub.br2{background:#fff8e1;border-left:3px solid var(--s);border-radius:12px;
  align-self:flex-start;color:#333;font-size:11px;
  opacity:0;transform:translateX(-10px);transition:all .35s ease;}
.bub.show{opacity:1;transform:none;}
.typ{align-self:flex-end;display:flex;gap:4px;padding:7px 11px;
  background:rgba(6,199,85,.15);border-radius:12px;
  opacity:0;transition:opacity .3s;}
.typ.on{opacity:1;}
.dp{width:6px;height:6px;background:var(--g);border-radius:50%;animation:db 1s infinite;}
.dp:nth-child(2){animation-delay:.2s;}.dp:nth-child(3){animation-delay:.4s;}
@keyframes db{0%,60%,100%{transform:none}30%{transform:translateY(-5px)}}
.ph-in{background:#fff;padding:8px 12px;display:flex;gap:7px;align-items:center;
  border-top:1px solid #e8e8e8;}
.ph-in input{flex:1;border:1px solid #ddd;border-radius:16px;padding:6px 11px;font-size:11px;font-family:inherit;}
.ph-in .snd{width:30px;height:30px;border-radius:50%;background:var(--g);border:none;color:#fff;font-size:12px;}
.tech-panel{flex:1;display:flex;flex-direction:column;gap:11px;
  transform:translateX(-40px);opacity:0;transition:all .7s ease;}
.tech-panel.on{transform:none;opacity:1;}
.code-box{background:rgba(0,0,0,.55);border:1px solid rgba(255,255,255,.1);
  border-radius:11px;padding:14px 17px;font-size:12.5px;font-family:Consolas,monospace;
  color:#e2e8f0;line-height:1.75;opacity:0;transition:opacity .5s;}
.ck{color:var(--s);}.cv{color:#7fd7c9;}.cc{color:#475569;}.cw{color:#fff;}
.step-list{display:flex;flex-direction:column;gap:7px;}
.sti{display:flex;align-items:center;gap:10px;padding:9px 13px;
  background:rgba(255,255,255,.04);border-radius:9px;opacity:.2;
  transform:translateX(14px);transition:all .4s ease;}
.sti.on{opacity:1;transform:none;background:rgba(42,157,143,.08);}
.sti.dn{opacity:.55;transform:none;}
.sd{width:9px;height:9px;border-radius:50%;background:rgba(255,255,255,.2);flex-shrink:0;}
.sti.on .sd{background:var(--t);box-shadow:0 0 9px var(--t);}
.sti.dn .sd{background:#475569;}
.st{font-size:12.5px;color:#e2e8f0;flex:1;}
.sm{font-size:11px;color:#7fb8b2;}

/* ═══ S5: GUARDRAIL ═══ */
.guard-wrap{display:flex;gap:50px;align-items:center;z-index:2;width:1700px;}
.guard-left{display:flex;flex-direction:column;gap:14px;flex:1;}
.block-anim{display:flex;flex-direction:column;align-items:center;gap:16px;flex-shrink:0;}
.shield{font-size:100px;animation:shieldPulse 1.5s ease-in-out infinite;}
@keyframes shieldPulse{0%,100%{filter:drop-shadow(0 0 20px rgba(231,111,81,.4))}
  50%{filter:drop-shadow(0 0 50px rgba(231,111,81,.9));transform:scale(1.05);}}
.blocked-badge{background:var(--c);color:#fff;font-size:22px;font-weight:800;
  padding:12px 32px;border-radius:10px;letter-spacing:2px;
  animation:badgePop .4s cubic-bezier(.34,1.56,.64,1) forwards;opacity:0;}
@keyframes badgePop{from{opacity:0;transform:scale(.5)}to{opacity:1;transform:none}}
.timer-box{font-size:60px;font-weight:800;color:var(--c);text-align:center;
  text-shadow:0 0 30px rgba(231,111,81,.5);}
.timer-lbl{font-size:14px;color:#9fc5c0;margin-top:-8px;text-align:center;}

/* ═══ S6: DAILY BRIEFING ═══ */
.brief-wrap{display:flex;gap:50px;align-items:center;z-index:2;width:1700px;}
.brief-cards{flex:1;display:flex;flex-direction:column;gap:14px;}
.bcard{display:flex;gap:16px;align-items:flex-start;background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:18px 20px;
  opacity:0;transform:translateX(-20px);transition:all .5s ease;}
.bcard.on{opacity:1;transform:none;}
.bc-icon{font-size:32px;flex-shrink:0;margin-top:2px;}
.bc-text h4{font-size:16px;font-weight:700;color:#fff;}
.bc-text p{font-size:13px;color:#9fc5c0;margin-top:4px;line-height:1.5;}

/* ═══ S7: ADMIN ═══ */
.admin-shell{background:#fff;border-radius:14px;overflow:hidden;
  box-shadow:0 20px 60px rgba(0,0,0,.5);width:1640px;z-index:2;
  opacity:0;transform:translateY(30px);transition:all .7s ease;}
.admin-shell.on{opacity:1;transform:none;}
.adm-top{background:var(--d);padding:11px 18px;display:flex;align-items:center;gap:8px;}
.adot{width:11px;height:11px;border-radius:50%;}
.adm-nav{display:flex;gap:22px;margin-left:16px;font-size:12.5px;color:#9fc5c0;}
.aact{color:#fff;font-weight:700;border-bottom:2px solid var(--t);padding-bottom:2px;}
.adm-body{padding:18px 22px;}
.krow{display:flex;gap:12px;margin-bottom:14px;}
.kc{flex:1;background:#f5f9fa;border-radius:10px;padding:12px 14px;text-align:center;}
.kv{font-size:28px;font-weight:800;color:var(--d);}
.kl{font-size:11px;color:#6b7b86;margin-top:2px;}
table{width:100%;border-collapse:collapse;font-size:12.5px;}
th{background:#f5f9fa;color:#6b7b86;padding:7px 11px;text-align:left;font-size:11px;}
td{padding:8px 11px;border-bottom:1px solid #eef1f3;color:#1b2733;}
.rt{display:inline-block;padding:2px 7px;border-radius:4px;font-size:10.5px;font-weight:700;color:#fff;}

/* ═══ S8: CLOSE ═══ */
.close-wrap{text-align:center;z-index:2;}
.close-wrap h1{font-size:80px;font-weight:800;color:#fff;line-height:1.05;
  opacity:0;animation:titleIn .8s .2s cubic-bezier(.34,1.3,.64,1) forwards;}
.close-wrap .cs{font-size:24px;color:#9fc5c0;margin-top:14px;opacity:0;animation:fu .6s .9s ease forwards;}
.close-wrap .ct{font-size:18px;color:#7fb8b2;margin-top:8px;opacity:0;animation:fu .6s 1.2s ease forwards;}
.url-badge{display:inline-block;background:rgba(42,157,143,.15);border:1px solid var(--t);
  border-radius:10px;padding:14px 30px;font-size:20px;color:var(--s);font-weight:700;margin-top:24px;
  opacity:0;animation:fu .6s 1.5s ease forwards;}
</style>
</head>
<body>
<canvas id="cv"></canvas>
<div id="prog"></div>
<div id="nar"></div>
<div class="logo">🌾 ReLoop</div>
<div class="scene-lbl" id="slbl"></div>

<!-- S1: TITLE -->
<div class="sc on" id="s1">
  <div class="title-wrap">
    <h1>Re<em>Loop</em></h1>
    <div class="tw-sub">Safety-first AI for Thai farmers · via LINE</div>
    <div class="tw-th">ระบบ AI ที่ปลอดภัย สำหรับเกษตรกรไทย ผ่าน LINE</div>
    <div class="pill-row">
      <span class="pill" style="animation-delay:.15s">📱 LINE Messaging API</span>
      <span class="pill" style="animation-delay:.3s">🤖 Claude Sonnet 4.5 + Vision</span>
      <span class="pill" style="animation-delay:.45s">📚 RAG · OpenAI Embeddings</span>
      <span class="pill" style="animation-delay:.6s">🛡️ Hard Guardrails</span>
      <span class="pill" style="animation-delay:.75s">🌤️ Proactive Daily Briefing</span>
    </div>
  </div>
</div>

<!-- S2: PROBLEM -->
<div class="sc" id="s2">
  <div class="problem-wrap">
    <div class="prob-left">
      <h2 class="fade-up">Wrong advice <em>destroys harvests.</em></h2>
      <p class="fade-up" style="animation-delay:.3s">Thai farmers share advice in LINE groups daily. Much of it is unverified, commercially motivated, or outright false — leading to preventable crop losses and unsafe agrochemical use.</p>
      <div class="stat-grid">
        <div class="stat-box scale-in" style="animation-delay:.5s"><div class="sv">8.6M</div><div class="sl">farming households in Thailand</div></div>
        <div class="stat-box scale-in" style="animation-delay:.7s"><div class="sv">LINE</div><div class="sl">47M+ active users · rural adoption</div></div>
        <div class="stat-box scale-in" style="animation-delay:.9s"><div class="sv">70%</div><div class="sl">yield loss from viral false advice</div></div>
        <div class="stat-box scale-in" style="animation-delay:1.1s"><div class="sv">0</div><div class="sl">LLM tokens used for high-risk blocks</div></div>
      </div>
    </div>
    <div class="warn-list">
      <div class="warn-item slide-right" style="animation-delay:.6s">
        <div class="wi-icon">🧪</div>
        <div class="wi-text"><h4>"Mix X chemical at double dose for faster results"</h4><p>False. Double dosage causes crop burns, soil toxicity, and regulatory violations.</p></div>
      </div>
      <div class="warn-item slide-right" style="animation-delay:.85s">
        <div class="wi-icon">🌾</div>
        <div class="wi-text"><h4>"Cutting rice leaves increases yield"</h4><p>False. Viral video advice. Research confirms 20–40% yield reduction.</p></div>
      </div>
      <div class="warn-item slide-right" style="animation-delay:1.1s">
        <div class="wi-icon">🧴</div>
        <div class="wi-text"><h4>"Unregistered cheap pesticides work better"</h4><p>False and illegal. Possession carries up to 10 years imprisonment in Thailand.</p></div>
      </div>
    </div>
  </div>
</div>

<!-- S3: PIPELINE -->
<div class="sc" id="s3">
  <div class="pipe-wrap">
    <div class="pipe-intro fade-up">End-to-end request pipeline — every farmer message follows this path</div>
    <div class="pipe-row">
      <div class="pnode" id="p1"><div class="pn-icon">📱</div><div class="pn-title">LINE Platform</div><div class="pn-sub">POST /webhook/line<br/>HMAC-SHA256<br/>signature verify</div><span class="pn-badge bk" id="pb1">✓ Verified</span></div>
      <div class="parr" id="a1"><svg viewBox="0 0 24 16"><line class="al" x1="0" y1="8" x2="18" y2="8"/><polygon class="ah" points="16,4 24,8 16,12"/></svg></div>
      <div class="pnode" id="p2"><div class="pn-icon">🔁</div><div class="pn-title">Deduplication</div><div class="pn-sub">message.id check<br/>PostgreSQL<br/>idempotency</div><span class="pn-badge bk" id="pb2">✓ New</span></div>
      <div class="parr" id="a2"><svg viewBox="0 0 24 16"><line class="al" x1="0" y1="8" x2="18" y2="8"/><polygon class="ah" points="16,4 24,8 16,12"/></svg></div>
      <div class="pnode" id="p3"><div class="pn-icon">🛡️</div><div class="pn-title">Safety Gate</div><div class="pn-sub">keyword blocklist<br/>pesticide · medical<br/>legal · financial</div><span class="pn-badge bk" id="pb3">✓ Safe</span></div>
      <div class="parr" id="a3"><svg viewBox="0 0 24 16"><line class="al" x1="0" y1="8" x2="18" y2="8"/><polygon class="ah" points="16,4 24,8 16,12"/></svg></div>
      <div class="pnode" id="p4"><div class="pn-icon">🎯</div><div class="pn-title">Intent Classify</div><div class="pn-sub">domain / smalltalk<br/>help / image<br/>keyword-based</div><span class="pn-badge bk" id="pb4">domain</span></div>
      <div class="parr" id="a4"><svg viewBox="0 0 24 16"><line class="al" x1="0" y1="8" x2="18" y2="8"/><polygon class="ah" points="16,4 24,8 16,12"/></svg></div>
      <div class="pnode" id="p5"><div class="pn-icon">🔍</div><div class="pn-title">RAG Retrieval</div><div class="pn-sub">OpenAI embeddings<br/>cosine similarity<br/>min_score=0.18</div><span class="pn-badge bk" id="pb5">4 chunks · 0.41</span></div>
      <div class="parr" id="a5"><svg viewBox="0 0 24 16"><line class="al" x1="0" y1="8" x2="18" y2="8"/><polygon class="ah" points="16,4 24,8 16,12"/></svg></div>
      <div class="pnode" id="p6"><div class="pn-icon">🤖</div><div class="pn-title">Claude Sonnet 4.5</div><div class="pn-sub">grounded generation<br/>citation mandatory<br/>3-turn history</div><span class="pn-badge bk" id="pb6">✓ 340ms</span></div>
      <div class="parr" id="a6"><svg viewBox="0 0 24 16"><line class="al" x1="0" y1="8" x2="18" y2="8"/><polygon class="ah" points="16,4 24,8 16,12"/></svg></div>
      <div class="pnode" id="p7"><div class="pn-icon">💬</div><div class="pn-title">LINE Reply API</div><div class="pn-sub">reply_token used<br/>push API for images<br/>PostgreSQL log</div><span class="pn-badge bk" id="pb7">✓ Sent</span></div>
    </div>
    <div class="pipe-stats">
      <div class="ps" style="animation-delay:3.5s"><div class="pv">25</div><div class="pl">Thai agriculture FAQ entries</div></div>
      <div class="ps" style="animation-delay:3.7s"><div class="pv">1536</div><div class="pl">embedding dimensions</div></div>
      <div class="ps" style="animation-delay:3.9s"><div class="pv">340ms</div><div class="pl">avg end-to-end latency</div></div>
      <div class="ps" style="animation-delay:4.1s"><div class="pv">0</div><div class="pl">LLM tokens for high-risk</div></div>
    </div>
    <div class="pipe-notes">
      <div class="pnote" style="animation-delay:4.3s">📊 Every message logged: route · confidence · latency · citations → PostgreSQL audit trail</div>
      <div class="pnote" style="animation-delay:4.5s">📅 First message of day → daily briefing prepended (Chiang Mai weather · govt incentives · false news)</div>
      <div class="pnote" style="animation-delay:4.7s">🔒 PDPA: pseudonymous LINE user IDs only · purpose-based consent · erasure cascade</div>
    </div>
  </div>
</div>

<!-- S4: LIVE DEMO -->
<div class="sc" id="s4">
  <div class="scene-lbl-inner" style="position:absolute;top:32px;left:52px;font-size:12px;font-weight:700;color:var(--s);letter-spacing:3px;text-transform:uppercase;">LIVE DEMO · Domain Question Flow</div>
  <div class="demo-wrap">
    <div class="phone" id="ph">
      <div class="ph-bar"><div class="ph-av">🌾</div><div><div class="ph-nm">ReLoop</div><div class="ph-sb" id="ph-sb">Online</div></div></div>
      <div class="chat" id="chat"></div>
      <div class="ph-in"><input id="ph-inp" value="" readonly/><div class="snd">➤</div></div>
    </div>
    <div class="tech-panel" id="tp">
      <div class="code-box" id="cb1">
        <span class="cc">// 1. LINE sends signed POST to /webhook/line</span><br/>
        <span class="ck">"text"</span>: <span class="cv">"ข้าวในนาใบเหลืองครับ"</span>,<br/>
        <span class="ck">"line_user_id"</span>: <span class="cv">"U9f2d4a3..."</span>,&nbsp;<span class="ck">"line_message_id"</span>: <span class="cv">"502481..."</span>
      </div>
      <div class="step-list">
        <div class="sti" id="st1"><div class="sd"></div><div class="st">🛡️ is_high_risk(text) → <span style="color:var(--t)">False</span> — proceed</div><div class="sm">&lt;1ms</div></div>
        <div class="sti" id="st2"><div class="sd"></div><div class="st">🎯 classify_intent(text) → <span style="color:var(--s)">domain</span> — route to RAG</div><div class="sm">&lt;1ms</div></div>
        <div class="sti" id="st3"><div class="sd"></div><div class="st">🔍 search(db, top_k=4, min_score=0.18) → <span style="color:var(--t)">4 chunks · conf=0.41</span></div><div class="sm">12ms</div></div>
        <div class="sti" id="st4"><div class="sd"></div><div class="st">🤖 AnthropicLLM.generate(text, context_chunks) → grounded Thai reply</div><div class="sm">328ms</div></div>
        <div class="sti" id="st5"><div class="sd"></div><div class="st">💾 log_outbound(route=<span style="color:var(--t)">faq_grounded</span>, confidence=0.41, citations=4)</div><div class="sm">2ms</div></div>
      </div>
      <div class="code-box" id="cb2">
        <span class="cc">// Response</span>&nbsp;
        <span class="ck">"route"</span>: <span class="cv">"faq_grounded"</span>,&nbsp;
        <span class="ck">"confidence"</span>: <span style="color:var(--t)">0.41</span>,&nbsp;
        <span class="ck">"latency_ms"</span>: <span style="color:var(--t)">340</span>,&nbsp;
        <span class="ck">"citations"</span>: <span style="color:var(--t)">4</span>
      </div>
    </div>
  </div>
</div>

<!-- S5: GUARDRAIL -->
<div class="sc" id="s5">
  <div class="scene-lbl-inner" style="position:absolute;top:32px;left:52px;font-size:12px;font-weight:700;color:var(--s);letter-spacing:3px;text-transform:uppercase;">GUARDRAIL · HIGH-RISK REFUSED IN &lt;5ms</div>
  <div class="guard-wrap">
    <div class="guard-left">
      <div class="code-box" id="g-code" style="opacity:0;transition:opacity .6s;">
        <span class="cc">// Safety gate runs BEFORE retrieval or LLM</span><br/>
        <span class="cw">if</span> <span class="ck">is_high_risk</span>(text):&nbsp;<span class="cc"># "พาราควอต" ∈ HIGH_RISK_KEYWORDS</span><br/>
        &nbsp;&nbsp;<span class="cw">return</span> AgentResult(<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;reply=<span style="color:var(--c)">HIGH_RISK_RESPONSE_TH</span>,&nbsp;<span class="cc"># fixed template</span><br/>
        &nbsp;&nbsp;&nbsp;&nbsp;route=<span class="cv">"refused"</span>, intent=<span class="cv">"high_risk"</span><br/>
        &nbsp;&nbsp;)&nbsp;<span class="cc"># LLM tokens: 0 · time: &lt;5ms</span>
      </div>
      <div class="step-list" style="margin-top:2px;">
        <div class="sti" id="g1"><div class="sd"></div><div class="st">Keyword scan: "พาราควอต" matched HIGH_RISK_KEYWORDS</div><div class="sm">&lt;1ms</div></div>
        <div class="sti" id="g2" style="background:rgba(231,111,81,.08)!important"><div class="sd" style="background:var(--c);box-shadow:0 0 9px var(--c)"></div><div class="st" style="color:#f4a896;"><b>LLM CALL SKIPPED</b> — fixed Thai refusal template returned immediately</div><div class="sm">&lt;5ms</div></div>
        <div class="sti" id="g3"><div class="sd"></div><div class="st">Logged: route="refused" intent="high_risk" → admin visible</div><div class="sm">1ms</div></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:12px;" id="g-metrics" style="opacity:0;transition:opacity .5s;">
        <div style="background:rgba(231,111,81,.12);border:1px solid rgba(231,111,81,.3);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:30px;font-weight:800;color:var(--c)">0</div><div style="font-size:11px;color:#f4a896;margin-top:3px">LLM tokens used</div></div>
        <div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:30px;font-weight:800;color:#fff">&lt;5ms</div><div style="font-size:11px;color:#9fc5c0;margin-top:3px">Total latency</div></div>
        <div style="background:rgba(231,111,81,.12);border:1px solid rgba(231,111,81,.3);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:30px;font-weight:800;color:var(--c)">100%</div><div style="font-size:11px;color:#f4a896;margin-top:3px">Refusal rate (high-risk)</div></div>
        <div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:30px;font-weight:800;color:#fff">4</div><div style="font-size:11px;color:#9fc5c0;margin-top:3px">Risk categories blocked</div></div>
      </div>
    </div>
    <div class="block-anim">
      <div class="shield" id="shield" style="opacity:0;transition:opacity .4s;">🛡️</div>
      <div id="blocked" style="opacity:0;transition:opacity .4s;">
        <div class="blocked-badge" style="animation:none;opacity:1;">⛔ BLOCKED</div>
      </div>
      <div class="timer-box" id="g-timer">0ms</div>
      <div class="timer-lbl">time to refusal</div>
    </div>
  </div>
</div>

<!-- S6: DAILY BRIEFING -->
<div class="sc" id="s6">
  <div class="brief-wrap">
    <div class="phone" style="opacity:1;transform:none;">
      <div class="ph-bar"><div class="ph-av">🌾</div><div><div class="ph-nm">ReLoop</div><div class="ph-sb">Online</div></div></div>
      <div class="chat">
        <div class="bub br2 show" style="font-size:11px;line-height:1.65;opacity:1;transform:none;">
          🌾 <b>ข้อมูลเกษตรกรประจำวัน</b> · 17/07/2026<br/>
          ────────────────────────<br/><br/>
          🌤️ <b>สภาพอากาศเชียงใหม่</b><br/>
          อากาศร้อนชื้น · 33°C (รู้สึก 36°C) · ความชื้น 72%<br/><br/>
          📢 <b>มาตรการรัฐบาล</b><br/>
          ประกันรายได้ชาวนา 10,000 บาท/ตัน ลงทะเบียน ธกส.<br/><br/>
          ⚠️ <b>ข่าวลือที่ควรระวัง</b><br/>
          น้ำหมักผลไม้ไม่ทดแทนปุ๋ยเคมีได้ 100%
        </div>
        <div class="bub u show" style="opacity:1;transform:none;">ดินในนาผมเป็นกรดครับ แก้ยังไงดี</div>
        <div class="bub b show" style="font-size:11.5px;line-height:1.6;opacity:1;transform:none;">
          ดินเปรี้ยว pH ต่ำกว่า 5.5 แก้ด้วย:<br/>
          ใส่โดโลไมท์ 200–300 กก./ไร่<br/>
          ไถกลบก่อนปักดำ 2–4 สัปดาห์<br/><br/>
          📎 แหล่งข้อมูล: กรมพัฒนาที่ดิน
        </div>
      </div>
      <div class="ph-in"><input value="" readonly/><div class="snd">➤</div></div>
    </div>
    <div class="brief-cards">
      <div class="bcard" id="bc1">
        <div class="bc-icon">🌤️</div>
        <div class="bc-text"><h4>Chiang Mai Weather</h4><p>Real-time temperature, humidity, and conditions via OpenWeatherMap API. Farmers know what field conditions to expect before they go out.</p></div>
      </div>
      <div class="bcard" id="bc2">
        <div class="bc-icon">📢</div>
        <div class="bc-text"><h4>Government Incentives</h4><p>Latest subsidies, income-guarantee programs, and BAAC loan schemes — curated by admins in the FAQ portal. Farmers never miss a benefit they're entitled to.</p></div>
      </div>
      <div class="bcard" id="bc3">
        <div class="bc-icon">⚠️</div>
        <div class="bc-text"><h4>False News Alerts</h4><p>Verified alerts about misinformation circulating in LINE groups — fake fertiliser claims, unlicensed chemicals, unverified viral advice. Flagged by experts before it spreads.</p></div>
      </div>
      <div class="bcard" id="bc4" style="border-color:rgba(42,157,143,.3);">
        <div class="bc-icon">⏰</div>
        <div class="bc-text"><h4>Automatic · once per day · Bangkok time</h4><p>Sent as the first LINE bubble on each farmer's first message of the day. No subscription needed — just use ReLoop normally and it arrives.</p></div>
      </div>
    </div>
  </div>
</div>

<!-- S7: ADMIN -->
<div class="sc" id="s7">
  <div style="display:flex;justify-content:center;width:100%;z-index:2;">
    <div class="admin-shell" id="adm">
      <div class="adm-top">
        <div class="adot" style="background:#e76f51;"></div>
        <div class="adot" style="background:var(--s);"></div>
        <div class="adot" style="background:var(--t);"></div>
        <div class="adm-nav">
          <span>Conversations</span><span>FAQ (25)</span>
          <span>⚖️ Compare LLMs</span><span class="aact">📊 Stats</span><span>Logout</span>
        </div>
      </div>
      <div class="adm-body">
        <div class="krow">
          <div class="kc"><div class="kv" id="k1" style="color:var(--t)">0</div><div class="kl">Sessions</div></div>
          <div class="kc"><div class="kv" id="k2">0</div><div class="kl">Questions today</div></div>
          <div class="kc"><div class="kv" id="k3" style="color:var(--t)">0%</div><div class="kl">Grounding rate</div></div>
          <div class="kc"><div class="kv" id="k4" style="color:var(--c)">0%</div><div class="kl">Refusal rate</div></div>
          <div class="kc"><div class="kv" id="k5">0ms</div><div class="kl">Avg latency</div></div>
          <div class="kc"><div class="kv" id="k6" style="color:var(--t)">0</div><div class="kl">FAQ entries</div></div>
        </div>
        <table>
          <tr><th>Session</th><th>Farmer</th><th>Question</th><th>Route</th><th>Confidence</th><th>Latency</th><th>Time</th></tr>
          <tr><td>a1b2c3</td><td>U9f2d4a…</td><td>ข้าวในนาใบเหลืองครับ ทำอย่างไรดี</td><td><span class="rt" style="background:var(--t)">faq_grounded</span></td><td>0.41</td><td>340ms</td><td>09:14</td></tr>
          <tr><td>d4e5f6</td><td>U3a7b8c…</td><td>ใช้พาราควอตปริมาณเท่าไหร่ครับ</td><td><span class="rt" style="background:var(--c)">refused</span></td><td>—</td><td>&lt;5ms</td><td>08:52</td></tr>
          <tr><td>g7h8i9</td><td>Uf9e2d1…</td><td>🌾 Daily briefing + ดินในนาเป็นกรดครับ</td><td><span class="rt" style="background:var(--t)">faq_grounded</span></td><td>0.38</td><td>290ms</td><td>08:05</td></tr>
          <tr><td>j1k2l3</td><td>U4c6a9b…</td><td>[📷 Image: diseased rice leaf]</td><td><span class="rt" style="background:#8b5cf6">image_analysis</span></td><td>—</td><td>2.1s</td><td>07:40</td></tr>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- S8: CLOSE -->
<div class="sc" id="s8">
  <div class="close-wrap">
    <div style="font-size:14px;color:var(--s);font-weight:700;letter-spacing:4px;margin-bottom:16px;opacity:0;animation:fu .6s .0s ease forwards;">FACULTY OF AGRICULTURE · CHIANG MAI UNIVERSITY</div>
    <h1>Re<em style="color:var(--t);font-style:normal">Loop</em></h1>
    <div class="cs">Dr. Toungporn Uttarotai &amp; Dr. Daranrat Jaitiang</div>
    <div class="ct">ดร.ตวงพร อุตตโรทัย &amp; ดร.ดารารัตน์ ใจเที่ยง · คณะเกษตรศาสตร์ มช.</div>
    <div class="url-badge">thai-farmer-agent.onrender.com · LINE @643txfqa</div>
  </div>
</div>

<script>
/* ── PARTICLES ── */
const CV=document.getElementById('cv'),cx=CV.getContext('2d');
CV.width=1920;CV.height=1080;
const pts=Array.from({length:65},()=>({x:Math.random()*1920,y:Math.random()*1080,
  vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,r:Math.random()*1.8+.8}));
function drawP(){
  cx.clearRect(0,0,1920,1080);
  pts.forEach(p=>{p.x+=p.vx;p.y+=p.vy;
    if(p.x<0||p.x>1920)p.vx*=-1;if(p.y<0||p.y>1080)p.vy*=-1;
    cx.beginPath();cx.arc(p.x,p.y,p.r,0,Math.PI*2);
    cx.fillStyle='rgba(42,157,143,.5)';cx.fill();});
  pts.forEach((a,i)=>pts.slice(i+1).forEach(b=>{
    const d=Math.hypot(a.x-b.x,a.y-b.y);
    if(d<120){cx.beginPath();cx.moveTo(a.x,a.y);cx.lineTo(b.x,b.y);
    cx.strokeStyle=`rgba(42,157,143,${.3*(1-d/120)})`;cx.lineWidth=.6;cx.stroke();}}));
  requestAnimationFrame(drawP);}
drawP();

/* ── NARRATION SUBTITLES ── */
const NAR_DATA=[
  [500,   7500,  "Welcome to ReLoop — a safety-first AI assistant that helps Thai farmers get trusted agricultural advice, directly on LINE."],
  [8500,  17000, "Thailand has 8.6 million farming households. Many rely on unverified advice in LINE groups — leading to crop losses and unsafe agrochemical use."],
  [18500, 32000, "Every message flows through a 7-stage pipeline: verified, deduplicated, safety-checked, intent-classified, retrieved via RAG, generated by Claude, then replied to the farmer."],
  [33500, 52000, "A farmer asks about yellow rice leaves. The question passes the safety gate, is matched against 25 expert-reviewed FAQ entries, and Claude generates a grounded answer — with a full source citation."],
  [53500, 64000, "High-risk questions — like exact pesticide dosages — are blocked in under 5 milliseconds. The AI is never called. A fixed safety template is returned immediately."],
  [65500, 74000, "Every morning, farmers receive a proactive daily briefing: Chiang Mai weather, government incentives, and false news alerts — curated by agricultural experts."],
  [75500, 84000, "Administrators review all conversations, manage the knowledge base, compare Claude versus GPT-4 side by side, and monitor real-time grounding and refusal rates."],
  [85500, 91500, "ReLoop. Built by Dr. Toungporn Uttarotai and Dr. Daranrat Jaitiang, Faculty of Agriculture, Chiang Mai University. Live now."],
];
const narEl=document.getElementById('nar');
function showNar(text){narEl.style.opacity='0';setTimeout(()=>{narEl.textContent=text;narEl.style.opacity='1';},300);}
function hideNar(){narEl.style.opacity='0';}

/* ── PROGRESS BAR ── */
const progEl=document.getElementById('prog');
const TOTAL=92000;
const t0=performance.now();
function tickProg(){
  const e=performance.now()-t0;
  progEl.style.width=Math.min(100,e/TOTAL*100)+'%';
  if(e<TOTAL)requestAnimationFrame(tickProg);}
requestAnimationFrame(tickProg);

/* ── SCENE SCHEDULE ── */
/* at: start ms, scene id to show, label text, callback */
const SCHED=[
  {at:0,    sc:'s1', lbl:''},
  {at:8000, sc:'s2', lbl:'The Problem'},
  {at:18000,sc:'s3', lbl:'System Architecture'},
  {at:33000,sc:'s4', lbl:'Live Demo'},
  {at:53000,sc:'s5', lbl:'Safety Guardrail'},
  {at:65000,sc:'s6', lbl:'Daily Briefing'},
  {at:75000,sc:'s7', lbl:'Admin Portal'},
  {at:85000,sc:'s8', lbl:''},
];

let curSc='s1';
const lbl=document.getElementById('slbl');
function showSc(id,labelTxt){
  document.getElementById(curSc).classList.remove('on');
  curSc=id;
  document.getElementById(id).classList.add('on');
  lbl.textContent=labelTxt;
  lbl.style.opacity=labelTxt?'1':'0';
  onShow(id);}

/* ── SCENE-SPECIFIC ANIMATIONS ── */
function onShow(id){
  if(id==='s3'){
    for(let i=1;i<=7;i++){
      setTimeout(()=>{
        const n=document.getElementById('p'+i);
        const a=document.getElementById('a'+i);
        const b=document.getElementById('pb'+i);
        n.classList.add('show','glow');
        if(a)a.classList.add('on');
        if(b)b.style.display='inline-block';
        setTimeout(()=>n.classList.remove('glow'),600);
      },200+i*1100);}
  }
  if(id==='s4'){
    const ph=document.getElementById('ph');
    const tp=document.getElementById('tp');
    const chat=document.getElementById('chat');
    const inp=document.getElementById('ph-inp');
    setTimeout(()=>{ph.classList.add('on');tp.classList.add('on');},200);
    // Daily briefing bubble
    setTimeout(()=>addBub(chat,'br2','🌾 <b>ข้อมูลประจำวัน</b> · 17/07/2026<br/>🌤️ เชียงใหม่ 33°C · ความชื้น 72%<br/>📢 ประกันรายได้ชาวนา 10,000 บาท/ตัน'),700);
    // Typewriter input
    setTimeout(()=>{
      document.getElementById('cb1').style.opacity='1';
      typeInput(inp,'ข้าวในนาใบเหลืองครับ ทำอย่างไรดี',55,()=>{
        addBub(chat,'u','ข้าวในนาใบเหลืองครับ ทำอย่างไรดี');
        inp.value='';
        // Steps
        const stps=['st1','st2','st3','st4','st5'];
        stps.forEach((s,i)=>setTimeout(()=>{
          document.getElementById(s).classList.add('on');
          if(i>0)document.getElementById(stps[i-1]).classList.replace('on','dn');
        },400+i*650));
        // Typing indicator
        addTyping(chat,400,3000);
        // Bot reply
        setTimeout(()=>addBub(chat,'b',
          'ใบข้าวเหลืองมีสาเหตุหลัก 3 ประการ:<br/><br/>(1) <b>ขาดธาตุไนโตรเจน</b> — ใส่ปุ๋ยยูเรีย 3–5 กก./ไร่<br/>(2) <b>น้ำท่วมขัง</b> — ระบายน้ำออกทันที<br/>(3) <b>ดินเป็นกรด</b> — ใส่ปูนขาว 100–200 กก./ไร่<br/><br/>📎 แหล่งข้อมูล: กรมการข้าว'),3600);
        setTimeout(()=>document.getElementById('cb2').style.opacity='1',4400);
      });
    },1400);}
  if(id==='s5'){
    setTimeout(()=>document.getElementById('g-code').style.opacity='1',300);
    ['g1','g2','g3'].forEach((g,i)=>setTimeout(()=>{
      document.getElementById(g).classList.add('on');
      if(i>0)document.getElementById(['g1','g2','g3'][i-1]).classList.replace('on','dn');
    },600+i*900));
    const sh=document.getElementById('shield');
    const bl=document.getElementById('blocked');
    const tm=document.getElementById('g-timer');
    setTimeout(()=>{sh.style.opacity='1';},600);
    setTimeout(()=>{bl.style.opacity='1';},2800);
    // Timer count 0→5ms
    let v=0;const iv=setInterval(()=>{
      tm.textContent=v+'ms';v++;if(v>5){clearInterval(iv);tm.textContent='&lt;5ms';}
    },120);
    setTimeout(()=>document.getElementById('g-metrics').style.opacity='1',3200);}
  if(id==='s6'){
    ['bc1','bc2','bc3','bc4'].forEach((b,i)=>
      setTimeout(()=>document.getElementById(b).classList.add('on'),300+i*500));}
  if(id==='s7'){
    setTimeout(()=>{
      const adm=document.getElementById('adm');
      adm.classList.add('on');
      cTo('k1',24,'',700);cTo('k2',156,'',700);cTo('k6',25,'',500);
      setTimeout(()=>{document.getElementById('k3').textContent='83%';},600);
      setTimeout(()=>{document.getElementById('k4').textContent='9%';},800);
      setTimeout(()=>{document.getElementById('k5').textContent='340ms';},1000);
    },200);}
}

function cTo(id,target,sfx,ms){
  let v=0,s=Math.ceil(target/28);const el=document.getElementById(id);
  const iv=setInterval(()=>{v=Math.min(v+s,target);el.textContent=v+sfx;if(v>=target)clearInterval(iv);},ms/28);}

function addBub(chat,cls,html){
  const d=document.createElement('div');
  d.className='bub '+cls;d.innerHTML=html;
  chat.appendChild(d);
  setTimeout(()=>d.classList.add('show'),10);
  chat.scrollTop=chat.scrollHeight;}

function addTyping(chat,delay,dur){
  let el;
  setTimeout(()=>{
    el=document.createElement('div');el.className='typ';
    el.innerHTML='<div class="dp"></div><div class="dp"></div><div class="dp"></div>';
    chat.appendChild(el);setTimeout(()=>el.classList.add('on'),10);
    chat.scrollTop=chat.scrollHeight;},delay);
  setTimeout(()=>{if(el&&el.parentNode){el.classList.remove('on');setTimeout(()=>el.parentNode&&el.parentNode.removeChild(el),300);}},delay+dur);}

function typeInput(inp,txt,spd,cb){
  let i=0;inp.value='';
  function s(){if(i<txt.length){inp.value+=txt[i++];setTimeout(s,spd);}else if(cb)cb();}s();}

/* ── MAIN TIMELINE ── */
function at(ms,fn){setTimeout(fn,ms);}

// Scene transitions
SCHED.forEach(ev=>at(ev.at,()=>showSc(ev.sc,ev.lbl)));

// Narration subtitles
NAR_DATA.forEach(([s,e,text])=>{
  at(s,()=>showNar(text));
  at(e,()=>hideNar());});
</script>
</body>
</html>
'''

# ─── TTS GENERATION ───────────────────────────────────────────────────────────
async def gen_tts():
    import edge_tts, asyncio
    VOICE = "en-US-JennyNeural"
    TEXTS = [seg[2] for seg in NARRATION]
    STARTS = [seg[0]/1000 for seg in NARRATION]  # seconds

    tts_dir = BASE / "tts_parts"
    tts_dir.mkdir(exist_ok=True)

    print("Generating TTS narration...")
    for i, text in enumerate(TEXTS):
        out = tts_dir / f"part_{i:02d}.mp3"
        communicate = edge_tts.Communicate(text, VOICE, rate="+5%")
        await communicate.save(str(out))
        print(f"  TTS {i+1}/{len(TEXTS)}: {out.name}")

    # Build a silent base track (TOTAL_MS ms)
    silence = tts_dir / "silence.mp3"
    subprocess.run([str(FFMPEG),"-y","-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",str(TOTAL_MS/1000),"-q:a","9","-acodec","libmp3lame",str(silence)],
        capture_output=True)

    # Mix each TTS part at its start time using amix/adelay
    # Build a complex filter that delays each part and mixes them all
    inputs = ["-i", str(silence)]
    for i in range(len(TEXTS)):
        inputs += ["-i", str(tts_dir / f"part_{i:02d}.mp3")]

    delay_ms = int(STARTS[0] * 1000)
    filter_parts = [f"[1:a]adelay={int(STARTS[0]*1000)}|{int(STARTS[0]*1000)}[a0]"]
    for i in range(1, len(TEXTS)):
        d = int(STARTS[i]*1000)
        filter_parts.append(f"[{i+1}:a]adelay={d}|{d}[a{i}]")
    mix_inputs = "".join(f"[a{i}]" for i in range(len(TEXTS)))
    filter_parts.append(f"[0:a]{mix_inputs}amix=inputs={len(TEXTS)+1}:normalize=0[aout]")
    f_complex = ";".join(filter_parts)

    narration_out = tts_dir / "narration.mp3"
    cmd = [str(FFMPEG),"-y"] + inputs + [
        "-filter_complex", f_complex,
        "-map","[aout]","-t",str(TOTAL_MS/1000),
        "-q:a","2", str(narration_out)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("TTS mix error:", result.stderr[-400:])
        return None
    print(f"Narration audio: {narration_out}")
    return narration_out


# ─── VIDEO RECORDING ─────────────────────────────────────────────────────────
async def record_video():
    from playwright.async_api import async_playwright

    rec_dir = BASE / "demo_recording"
    rec_dir.mkdir(exist_ok=True)
    url = (BASE / "demo.html").resolve().as_uri()

    print(f"Recording demo at {W}x{H} for {TOTAL_MS//1000}s...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(rec_dir),
            record_video_size={"width": W, "height": H},
        )
        page = await ctx.new_page()
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(TOTAL_MS + 1000)
        await ctx.close()
        await browser.close()

    webms = sorted(rec_dir.glob("*.webm"))
    if not webms:
        print("ERROR: no webm recorded")
        return None
    webm = webms[-1]
    print(f"Recorded: {webm.name} ({webm.stat().st_size//1024}KB)")
    return webm


# ─── MERGE VIDEO + AUDIO ──────────────────────────────────────────────────────
def merge(webm: pathlib.Path, audio: pathlib.Path):
    cmd = [str(FFMPEG),"-y",
        "-i", str(webm),
        "-i", str(audio),
        "-c:v","libx264","-preset","medium","-crf","20",
        "-vf", f"scale={W}:{H}:flags=lanczos,format=yuv420p",
        "-r","30",
        "-c:a","aac","-b:a","192k",
        "-shortest","-movflags","+faststart",
        str(OUT_MP4)]
    print("Merging video + audio...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Merge error:", result.stderr[-500:])
    else:
        mb = OUT_MP4.stat().st_size / 1024 / 1024
        print(f"\n✅ demo.mp4 ready: {OUT_MP4}  ({mb:.1f} MB)")
    # Cleanup
    shutil.rmtree(BASE/"demo_recording", ignore_errors=True)
    shutil.rmtree(BASE/"tts_parts", ignore_errors=True)


# ─── MAIN ────────────────────────────────────────────────────────────────────
async def main():
    # Write demo.html
    (BASE / "demo.html").write_text(DEMO_HTML, encoding="utf-8")
    print("demo.html written.")

    # Run TTS + video recording in parallel
    narration, webm = await asyncio.gather(gen_tts(), record_video())

    if webm and narration:
        merge(webm, narration)
    elif webm:
        # No audio — convert WebM to MP4 only
        cmd = [str(FFMPEG),"-y","-i",str(webm),
            "-vf",f"scale={W}:{H}:flags=lanczos,format=yuv420p",
            "-r","30","-c:v","libx264","-preset","medium","-crf","20",
            "-movflags","+faststart",str(OUT_MP4)]
        subprocess.run(cmd, capture_output=True)
        print(f"demo.mp4 (no audio): {OUT_MP4.stat().st_size//1024}KB")
        shutil.rmtree(BASE/"demo_recording", ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())

"""One-time LINE bot configuration script.

Sets up:
  1. Rich Menu — persistent 6-button panel at the bottom of every farmer's chat.
  2. Greeting message — sent automatically when a farmer first adds the bot.

Run once from the project root (with LINE credentials in .env or environment):
    .venv\Scripts\python tools\setup_line.py

Requires: LINE_CHANNEL_ACCESS_TOKEN in .env or environment.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path

# Load .env from project root
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for raw in _env.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
if not TOKEN:
    print("ERROR: LINE_CHANNEL_ACCESS_TOKEN not set in .env or environment.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

try:
    import httpx
except ImportError:
    print("Run from project venv: .venv\\Scripts\\python tools\\setup_line.py")
    sys.exit(1)


# ── Rich Menu Image (2500×1686, 3 cols × 2 rows) ─────────────────────────────

def make_rich_menu_image() -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    W, H = 2500, 1686
    COLS, ROWS = 3, 2
    CW, CH = W // COLS, H // ROWS

    # Colour palette
    BG       = (11, 58, 69)    # deep teal
    CELL_BG  = [
        (15, 76, 92),  (20, 90, 108), (13, 68, 82),
        (18, 84, 100), (23, 98, 116), (16, 72, 88),
    ]
    BORDER   = (42, 157, 143)  # bright teal
    TEXT_COL = (242, 246, 247)
    SUB_COL  = (191, 227, 221)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Try system fonts that support Thai (Windows + Linux fallbacks)
    def _font(size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    font_big  = _font(110)
    font_main = _font(80)
    font_sub  = _font(58)

    cells = [
        ("📅", "ข้อมูลประจำวัน",    "Daily Briefing"),
        ("🌾", "ถามเรื่องข้าว",      "Rice Questions"),
        ("🌱", "ถามเรื่องดินปุ๋ย",   "Soil & Fertiliser"),
        ("🐛", "ถามเรื่องแมลงศัตรู", "Pest & Disease"),
        ("�", "ส่งรูปพืช",          "Send Plant Photo"),
        ("❓", "วิธีใช้งาน",          "How It Works"),
    ]

    for idx, (emoji, thai, eng) in enumerate(cells):
        col = idx % COLS
        row = idx // COLS
        x0, y0 = col * CW, row * CH
        x1, y1 = x0 + CW, y0 + CH

        # Cell background
        draw.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=CELL_BG[idx])
        # Border
        draw.rectangle([x0, y0, x1, y1], outline=BORDER, width=6)

        # Emoji (rendered as text — may show as boxes on some systems but LINE renders fine)
        ew = font_big.getlength(emoji)
        draw.text((x0 + (CW - ew) / 2, y0 + CH * 0.12), emoji, font=font_big, fill=TEXT_COL)

        # Thai label
        tw = font_main.getlength(thai)
        draw.text((x0 + (CW - tw) / 2, y0 + CH * 0.45), thai, font=font_main, fill=TEXT_COL)

        # English sub-label
        sw = font_sub.getlength(eng)
        draw.text((x0 + (CW - sw) / 2, y0 + CH * 0.70), eng, font=font_sub, fill=SUB_COL)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Rich Menu definition ───────────────────────────────────────────────────────

CELL_W, CELL_H = 2500 // 3, 1686 // 2

BUTTON_MESSAGES = [
    "ข้อมูลประจำวัน",
    "ถามเรื่องข้าว ใบเหลือง โรคข้าว การเก็บเกี่ยว",
    "ถามเรื่องดินและปุ๋ย",
    "ถามเรื่องแมลงศัตรูพืชและการกำจัด",
    "📷 วิธีส่งรูปพืช: ถ่ายรูปพืชที่มีปัญหาแล้วส่งรูปมาที่แชทนี้ได้เลยครับ AI จะวิเคราะห์โรค แมลง หรือความผิดปกติให้",
    "วิธีใช้งาน",
]

RICH_MENU_DEF = {
    "size": {"width": 2500, "height": 1686},
    "selected": True,
    "name": "เมนูเกษตรกรไทย",
    "chatBarText": "📋 เมนู",
    "areas": [
        {
            "bounds": {
                "x": (idx % 3) * CELL_W,
                "y": (idx // 3) * CELL_H,
                "width": CELL_W,
                "height": CELL_H,
            },
            "action": {
                "type": "message",
                "text": BUTTON_MESSAGES[idx],
            },
        }
        for idx in range(6)
    ],
}

# ── Greeting message ───────────────────────────────────────────────────────────

GREETING = (
    "สวัสดีครับ! ยินดีต้อนรับสู่ระบบผู้ช่วยเกษตรกรไทย 🌾\n\n"
    "พัฒนาโดย ดร.ตวงพร อุตรโรตไทย และ ดร.ดารารัตน์ ใจเที่ยง\n"
    "คณะเกษตรศาสตร์ มหาวิทยาลัยเชียงใหม่\n\n"
    "✅ ถามได้เลย (พิมพ์เป็นภาษาไทย)\n"
    "• โรคพืช ใบเหลือง เชื้อรา แมลงศัตรู\n"
    "• ดิน ปุ๋ย การปรับปรุงดิน\n"
    "• การเก็บเกี่ยวและการดูแลพืช\n"
    "• สิทธิประโยชน์และมาตรการรัฐบาล\n\n"
    "📷 ส่งรูปภาพพืชได้เลย\n"
    "ถ่ายรูปพืชที่มีปัญหาแล้วส่งมา AI จะวิเคราะห์โรค แมลง หรือความผิดปกติให้ครับ\n\n"
    "📋 กดปุ่มเมนูด้านล่างเพื่อเริ่มต้น หรือพิมพ์ 'วิธีใช้งาน' เพื่อดูคำแนะนำ\n\n"
    "⚠️ ทุกคำตอบอ้างอิงจากข้อมูลที่ผ่านการตรวจสอบโดยผู้เชี่ยวชาญเท่านั้น\n"
    "คำถามที่มีความเสี่ยง (ปริมาณยา กฎหมาย การแพทย์) จะถูกส่งต่อผู้เชี่ยวชาญครับ"
)


# ── API helpers ────────────────────────────────────────────────────────────────

def api(method: str, path: str, **kwargs) -> dict:
    url = f"https://api.line.me{path}"
    resp = httpx.request(method, url, headers=HEADERS, timeout=30, **kwargs)
    if not resp.is_success:
        print(f"  ✗ {method} {path} → {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    return resp.json() if resp.text else {}


def upload_image(rich_menu_id: str, image_bytes: bytes) -> None:
    url = f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content"
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "image/png"},
        content=image_bytes,
        timeout=60,
    )
    if not resp.is_success:
        print(f"  ✗ image upload → {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    print("  ✓ Image uploaded")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n── Thai Farmer LINE Bot Setup ──────────────────────────")

    # 1. Delete existing default rich menu (if any)
    print("\n[1/5] Checking existing rich menus...")
    try:
        existing = api("GET", "/v2/bot/richmenu/list")
        for rm in existing.get("richmenus", []):
            api("DELETE", f"/v2/bot/richmenu/{rm['richMenuId']}")
            print(f"  ✓ Deleted old menu {rm['richMenuId']}")
    except Exception:
        pass

    # 2. Create rich menu
    print("\n[2/5] Creating rich menu definition...")
    result = api("POST", "/v2/bot/richmenu", json=RICH_MENU_DEF)
    rich_menu_id = result["richMenuId"]
    print(f"  ✓ Created {rich_menu_id}")

    # 3. Generate and upload image
    print("\n[3/5] Generating menu image...")
    image_bytes = make_rich_menu_image()
    # Save a copy locally so you can inspect it
    out = Path(__file__).parent / "richmenu_preview.png"
    out.write_bytes(image_bytes)
    print(f"  ✓ Saved preview → {out}")
    upload_image(rich_menu_id, image_bytes)

    # 4. Set as default for all users
    print("\n[4/5] Setting as default rich menu...")
    api("POST", f"/v2/bot/user/all/richmenu/{rich_menu_id}")
    print(f"  ✓ Set as default")

    # 5. Set greeting message (LINE OA Manager — can't be set via Messaging API)
    print("\n[5/5] Greeting message note:")
    print("  → Must be set via LINE OA Manager (not configurable via API).")
    print("  → Go to: https://manager.line.biz/")
    print("  → Your account → Settings → Greeting message → Edit")
    print("  → Paste this text:\n")
    print("─" * 60)
    print(GREETING)
    print("─" * 60)

    print("\n✅ Rich menu deployed successfully!")
    print(f"   Rich menu ID: {rich_menu_id}")
    print("   Open LINE on your phone and message the bot — you'll see the menu.\n")


if __name__ == "__main__":
    main()

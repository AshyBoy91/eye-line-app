"""Daily briefing: Chiang Mai weather + government incentives + false-news alerts.

Sent to each farmer on their FIRST interaction of each day (Bangkok time, UTC+7).
- Weather: OpenWeatherMap API (set OPENWEATHER_API_KEY; skipped if blank).
- Incentives & alerts: pulled from FAQ entries in categories
  `government_incentive` and `false_news_alert` (managed by admins via /admin/faq).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .config import settings
from .models import FaqDoc

_BKK = timezone(timedelta(hours=7))


def today_bangkok() -> "date":
    from datetime import date
    return datetime.now(_BKK).date()


def needs_daily_briefing(farmer) -> bool:
    return farmer.last_briefing_date != today_bangkok()


def mark_briefing_sent(db: DbSession, farmer) -> None:
    farmer.last_briefing_date = today_bangkok()
    db.flush()


def _weather() -> str:
    if not settings.openweather_api_key:
        return ""
    try:
        import httpx
        r = httpx.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": settings.openweather_city,
                "appid": settings.openweather_api_key,
                "units": "metric",
                "lang": "th",
            },
            timeout=8,
        )
        r.raise_for_status()
        d = r.json()
        desc = d["weather"][0]["description"]
        temp = round(d["main"]["temp"])
        feels = round(d["main"]["feels_like"])
        humidity = d["main"]["humidity"]
        wind = round(d["wind"]["speed"] * 3.6)  # m/s → km/h
        return (
            f"🌤️ สภาพอากาศเชียงใหม่วันนี้\n"
            f"{desc} · {temp}°C (รู้สึก {feels}°C)\n"
            f"ความชื้น {humidity}% · ลม {wind} กม./ชม."
        )
    except Exception:
        return ""


def _faq_section(db: DbSession, category: str, limit: int = 2) -> list[FaqDoc]:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(FaqDoc)
        .where(FaqDoc.category == category, FaqDoc.status == "published")
        .order_by(FaqDoc.updated_at.desc())
        .limit(limit)
    ).all()
    return [
        r for r in rows
        if (not r.valid_from or r.valid_from <= now)
        and (not r.valid_to or r.valid_to >= now)
    ]


def build_daily_briefing(db: DbSession) -> str:
    """Assemble the full briefing. Returns empty string if nothing to send."""
    parts: list[str] = []

    weather = _weather()
    if weather:
        parts.append(weather)

    incentives = _faq_section(db, "government_incentive")
    if incentives:
        lines = "\n".join(f"• {d.title}: {d.body_th[:130]}..." for d in incentives)
        parts.append(f"📢 มาตรการ/สิทธิประโยชน์รัฐบาล\n{lines}")

    alerts = _faq_section(db, "false_news_alert")
    if alerts:
        lines = "\n".join(f"• {d.title}: {d.body_th[:130]}..." for d in alerts)
        parts.append(f"⚠️ ข่าวลือ/ข้อมูลเท็จที่ควรระวัง\n{lines}")

    if not parts:
        return ""

    today_str = datetime.now(_BKK).strftime("%d/%m/%Y")
    header = f"🌾 ข้อมูลเกษตรกรประจำวัน · {today_str}\n{'─' * 28}"
    return header + "\n\n" + "\n\n".join(parts)

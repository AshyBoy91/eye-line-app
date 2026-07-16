"""Guardrails: intent classification and high-risk topic detection.

These are deliberately simple, table-driven rules so they are auditable and easy to
extend. In production the keyword lists should be maintained by domain experts and,
optionally, backed by a classifier — but the *policy* (refuse high-risk, ground
domain answers) must remain enforced in the orchestrator regardless of model output.
"""
from __future__ import annotations

# Topics that must never be answered by a generative model directly.
HIGH_RISK_KEYWORDS = [
    # pesticide / chemical dosage
    "ปริมาณยา", "โดสยา", "ผสมยาฆ่าแมลง", "อัตราการใช้สารเคมี", "สารเคมีอันตราย",
    "พาราควอต", "ไกลโฟเซต", "dosage", "how much pesticide", "mix chemical",
    # medical / human health
    "กินยา", "รักษาโรคคน", "อาการป่วย", "medicine dose", "medical",
    # legal / regulatory
    "กฎหมาย", "ฟ้องร้อง", "คดี", "legal advice", "lawsuit",
    # financial
    "กู้เงิน", "สินเชื่อ", "ลงทุนหุ้น", "ดอกเบี้ยเงินกู้", "loan", "invest",
]

# Signals that a message is a specific agriculture question (route to RAG).
DOMAIN_KEYWORDS = [
    "ข้าว", "นา", "ดิน", "ปุ๋ย", "โรคพืช", "แมลง", "ศัตรูพืช", "เพลี้ย",
    "ใบเหลือง", "ผลผลิต", "เพาะปลูก", "รดน้ำ", "พันธุ์", "เก็บเกี่ยว", "มันสำปะหลัง",
    "อ้อย", "ยางพารา", "ทุเรียน", "มะม่วง", "ผัก", "เชื้อรา", "วัชพืช",
    "rice", "soil", "fertilizer", "pest", "disease", "crop", "harvest",
]

GREETING_KEYWORDS = ["สวัสดี", "หวัดดี", "ขอบคุณ", "hello", "hi", "thanks", "ขอบใจ"]


def is_high_risk(text: str) -> bool:
    low = text.lower()
    return any(kw.lower() in low for kw in HIGH_RISK_KEYWORDS)


def classify_intent(text: str) -> str:
    """Return 'domain' for agriculture questions, else 'smalltalk'."""
    low = text.lower()
    if any(kw.lower() in low for kw in DOMAIN_KEYWORDS):
        return "domain"
    return "smalltalk"


HIGH_RISK_RESPONSE_TH = (
    "ขออภัยครับ คำถามนี้เกี่ยวข้องกับเรื่องที่ต้องใช้ความระมัดระวังเป็นพิเศษ "
    "(เช่น ปริมาณสารเคมี สุขภาพ กฎหมาย หรือการเงิน) "
    "เพื่อความปลอดภัย ผมไม่สามารถให้คำแนะนำที่เฉพาะเจาะจงได้ "
    "กรุณาติดต่อเจ้าหน้าที่ส่งเสริมการเกษตรหรือผู้เชี่ยวชาญโดยตรงครับ"
)

NO_ANSWER_RESPONSE_TH = (
    "ขออภัยครับ ยังไม่มีข้อมูลที่ตรงกับคำถามนี้ในคลังความรู้ "
    "คุณช่วยอธิบายเพิ่มเติม หรือสอบถามเจ้าหน้าที่ส่งเสริมการเกษตรในพื้นที่ได้ครับ"
)

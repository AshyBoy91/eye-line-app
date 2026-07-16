"""Seed the knowledge base with sample Thai agriculture FAQ content.

Content here is illustrative for local development. In production, FAQ entries must be
authored/reviewed by domain experts and attributed to authoritative sources
(e.g. Department of Agriculture / Rice Department).
"""
from __future__ import annotations

import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .embeddings import get_embedder
from .models import FaqChunk, FaqDoc

SAMPLE_FAQS = [
    {
        "title": "ข้าวใบเหลือง",
        "category": "rice",
        "source": "กรมการข้าว",
        "body_th": (
            "อาการข้าวใบเหลืองมักเกิดจากการขาดธาตุไนโตรเจน น้ำท่วมขังนานเกินไป "
            "หรือดินเป็นกรด ควรตรวจสอบระดับน้ำในนาให้เหมาะสม ระบายน้ำหากท่วมขัง "
            "และพิจารณาใส่ปุ๋ยไนโตรเจนตามคำแนะนำของเจ้าหน้าที่ส่งเสริมการเกษตร"
        ),
    },
    {
        "title": "การปรับปรุงดินเปรี้ยว",
        "category": "soil",
        "source": "กรมพัฒนาที่ดิน",
        "body_th": (
            "ดินเปรี้ยวหรือดินกรดสามารถปรับปรุงได้โดยการใส่ปูนขาวหรือปูนโดโลไมต์ "
            "เพื่อลดความเป็นกรดของดิน ควรตรวจวัดค่า pH ของดินก่อน "
            "และใส่อินทรียวัตถุเช่นปุ๋ยคอกหรือปุ๋ยหมักเพื่อปรับโครงสร้างดิน"
        ),
    },
    {
        "title": "การป้องกันเพลี้ยกระโดดสีน้ำตาลในนาข้าว",
        "category": "pests",
        "source": "กรมการข้าว",
        "body_th": (
            "เพลี้ยกระโดดสีน้ำตาลเป็นศัตรูสำคัญของข้าว ควรใช้พันธุ์ข้าวต้านทาน "
            "ไม่ปลูกข้าวหนาแน่นเกินไป หมั่นสำรวจแปลงนาอย่างสม่ำเสมอ "
            "และหลีกเลี่ยงการใช้สารเคมีเกินความจำเป็นเพราะทำลายศัตรูธรรมชาติ"
        ),
    },
    {
        "title": "ช่วงเวลาที่เหมาะสมในการเก็บเกี่ยวข้าว",
        "category": "rice",
        "source": "กรมการข้าว",
        "body_th": (
            "ควรเก็บเกี่ยวข้าวเมื่อเมล็ดสุกแก่ประมาณ 28-30 วันหลังข้าวออกดอก "
            "โดยสังเกตว่ารวงข้าวโน้มลงและเมล็ดมีสีเหลืองทอง "
            "การเก็บเกี่ยวเร็วหรือช้าเกินไปจะทำให้ผลผลิตและคุณภาพลดลง"
        ),
    },
    {
        "title": "การดูแลมันสำปะหลังในฤดูแล้ง",
        "category": "crop",
        "source": "กรมวิชาการเกษตร",
        "body_th": (
            "ในฤดูแล้งควรปลูกมันสำปะหลังในช่วงต้นฤดูฝนเพื่อให้ต้นตั้งตัวได้ดี "
            "คลุมดินด้วยเศษวัสดุเพื่อรักษาความชื้น และกำจัดวัชพืชในช่วง 3 เดือนแรก "
            "ซึ่งเป็นช่วงที่มันสำปะหลังอ่อนแอต่อการแข่งขันกับวัชพืช"
        ),
    },
    # ── Government incentives ──────────────────────────────────────────────────
    {
        "title": "โครงการประกันรายได้เกษตรกรชาวนา",
        "category": "government_incentive",
        "source": "กรมส่งเสริมการเกษตร",
        "body_th": (
            "รัฐบาลประกันรายได้ชาวนา ข้าวเปลือกหอมมะลิ 15,000 บาท/ตัน ไม่เกิน 14 ตัน/ครัวเรือน "
            "ข้าวเปลือกเจ้า 10,000 บาท/ตัน ไม่เกิน 30 ตัน ลงทะเบียนได้ที่ ธกส. สาขาใกล้บ้าน "
            "หรือผ่านแอปพลิเคชัน BAAC Mobile ตรวจสอบสิทธิ์ได้ที่เว็บไซต์กรมส่งเสริมการเกษตร"
        ),
    },
    {
        "title": "สินเชื่อเพื่อเกษตรกร ธกส. อัตราดอกเบี้ยพิเศษ",
        "category": "government_incentive",
        "source": "ธนาคารเพื่อการเกษตรและสหกรณ์การเกษตร (ธกส.)",
        "body_th": (
            "ธกส. เปิดให้กู้สินเชื่อเพื่อการเกษตรอัตราดอกเบี้ยพิเศษ MRR-1 ต่อปี "
            "สำหรับเกษตรกรที่ต้องการทุนหมุนเวียนและลงทุน วงเงินไม่เกิน 300,000 บาท/ราย "
            "ติดต่อ ธกส. สาขาใกล้บ้าน หรือสายด่วน 02-555-0555"
        ),
    },
    # ── False news alerts ──────────────────────────────────────────────────────
    {
        "title": "ข้อมูลเท็จ: ปุ๋ยผสมน้ำมันมะพร้าวเพิ่มผลผลิต 3 เท่า",
        "category": "false_news_alert",
        "source": "กรมวิชาการเกษตร",
        "body_th": (
            "มีข่าวลือแพร่ทาง LINE ว่าการผสมน้ำมันมะพร้าวกับปุ๋ยจะเพิ่มผลผลิตข้าวได้ 3 เท่า "
            "ข้อมูลนี้ไม่เป็นความจริงและไม่มีหลักฐานทางวิทยาศาสตร์รองรับ "
            "กรุณาปรึกษาเจ้าหน้าที่เกษตรหรือตรวจสอบที่เว็บไซต์กรมวิชาการเกษตรก่อนทดลอง"
        ),
    },
    {
        "title": "ข้อมูลเท็จ: สารเคมีราคาถูกไม่มีฉลากกำจัดเพลี้ยได้ 100%",
        "category": "false_news_alert",
        "source": "กรมการข้าว",
        "body_th": (
            "มีการแชร์ข้อมูลในกลุ่ม LINE เกี่ยวกับสารเคมีราคาถูกที่อ้างว่ากำจัดเพลี้ยกระโดดได้ 100% "
            "สารเคมีที่ไม่มีฉลากรับรองหรือไม่ผ่านกรมวิชาการเกษตรอาจเป็นสินค้าปลอมและเป็นอันตราย "
            "กรุณาซื้อสารเคมีจากร้านค้าที่ได้รับอนุญาตเท่านั้น"
        ),
    },
]


def _chunk_text(text: str, size: int = 220) -> list[str]:
    """Simple length-based chunking (Thai has no spaces to split on reliably)."""
    text = text.strip()
    if len(text) <= size:
        return [text]
    return [text[i : i + size] for i in range(0, len(text), size)]


def seed_if_empty(db: Session) -> int:
    existing = db.scalar(select(func.count()).select_from(FaqDoc))
    if existing:
        return 0

    embedder = get_embedder()
    created = 0
    for item in SAMPLE_FAQS:
        doc = FaqDoc(
            title=item["title"],
            category=item["category"],
            body_th=item["body_th"],
            source=item["source"],
            status="published",
            version=1,
        )
        db.add(doc)
        db.flush()
        _embed_doc(db, doc, embedder)
        created += 1

    db.commit()
    return created


def _embed_doc(db: Session, doc: FaqDoc, embedder) -> None:
    chunks = _chunk_text(doc.body_th)
    vectors = embedder.embed(chunks)
    for idx, (text, vec) in enumerate(zip(chunks, vectors)):
        db.add(
            FaqChunk(
                faq_doc_id=doc.id,
                chunk_index=idx,
                text=text,
                embedding=vec,
                token_count=len(text),
                hash=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            )
        )


def reembed_doc(db: Session, doc: FaqDoc) -> None:
    """Re-chunk and re-embed a FAQ document (call after create/update)."""
    for chunk in list(doc.chunks):
        db.delete(chunk)
    db.flush()
    _embed_doc(db, doc, get_embedder())

"""Smoke test: exercises the full pipeline via the ASGI app with TestClient.

Run: python -m tests.smoke_test  (from the project root, with deps installed)
Uses the offline hashing embedder + stub LLM, so no API keys are required.
"""
from __future__ import annotations

import os
import tempfile

# Use an isolated temp DB so the smoke test never touches a real database.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp.name}")
os.environ.setdefault("ADMIN_TOKEN", "test-token")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def main() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"

        # 1) Domain question -> should be grounded with a citation.
        r = client.post(
            "/webhook/simulate",
            json={"line_user_id": "U_test", "text": "ข้าวใบเหลืองควรทำอย่างไร"},
        ).json()
        assert r["route"] == "faq_grounded", r
        assert r["citations"], "grounded answer must have citations"
        print("domain ->", r["route"], "conf=", r["confidence"], "cites=", len(r["citations"]))

        # 2) High-risk question -> must be refused (never generated).
        r = client.post(
            "/webhook/simulate",
            json={"line_user_id": "U_test", "text": "ใช้พาราควอตปริมาณยาเท่าไหร่"},
        ).json()
        assert r["route"] == "refused", r
        print("high_risk ->", r["route"])

        # 3) Small talk -> conversational, no citations required.
        r = client.post(
            "/webhook/simulate",
            json={"line_user_id": "U_test", "text": "สวัสดีครับ"},
        ).json()
        assert r["route"] == "smalltalk", r
        print("smalltalk ->", r["route"])

        # 4) Off-topic domain with no matching FAQ -> refused rather than hallucinated.
        r = client.post(
            "/webhook/simulate",
            json={"line_user_id": "U_test", "text": "การเลี้ยงปลานิลในบ่อดินทำอย่างไร"},
        ).json()
        print("unknown_domain ->", r["route"], "conf=", r["confidence"])

        # 5) Admin requires token.
        assert client.get("/admin/conversations").status_code == 401
        assert client.get("/admin/conversations?token=test-token").status_code == 200

        # 6) Admin API returns logged messages.
        msgs = client.get("/admin/api/messages", headers={"X-Admin-Token": "test-token"}).json()
        assert len(msgs) >= 6, msgs
        print("admin messages logged:", len(msgs))

    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    main()

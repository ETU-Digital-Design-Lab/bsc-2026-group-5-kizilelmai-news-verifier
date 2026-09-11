"""
Admin Router — Raporlar ve şikayet yönetimi endpoint'leri.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
import jwt

from src.backend.auth import get_db_connection, SECRET_KEY, ALGORITHM
from src.backend.routers.auth import get_current_user, require_admin

router = APIRouter(tags=["admin"])


class ReportRequest(BaseModel):
    news_query: str
    news_details: Optional[str] = None
    report_reason: str
    source_id: Optional[int] = None


class ReportResponseRequest(BaseModel):
    admin_response: str
    status: str  # 'resolved', 'rejected', 'pending'


def _extract_user_email(req: Request) -> str:
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload.get("sub", "anonim")
        except Exception:
            pass
    return "anonim"


@router.post("/api/reports")
async def create_report(request: ReportRequest, req: Request):
    user_email = _extract_user_email(req)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reports (user_email, news_query, news_details, report_reason, source_id) VALUES (%s, %s, %s, %s, %s)",
            (user_email, request.news_query, request.news_details, request.report_reason, request.source_id),
        )
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Şikayetiniz başarıyla iletildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Şikayet iletilemedi: {str(e)}")


@router.get("/api/reports/my")
async def get_my_reports(page: int = 1, limit: int = 50, current_user: dict = Depends(get_current_user)):
    try:
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="Kullanıcı e-posta adresi bulunamadı.")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM reports WHERE user_email = %s", (user_email,))
        total_records = cursor.fetchone()[0]
        offset = (page - 1) * limit
        cursor.execute(
            """SELECT id, user_email, news_query, news_details, report_reason, admin_response,
                      status, source_id, created_at, updated_at
               FROM reports WHERE user_email = %s ORDER BY id DESC LIMIT %s OFFSET %s""",
            (user_email, limit, offset),
        )
        rows = cursor.fetchall()
        conn.close()
        return {
            "total": total_records, "page": page, "limit": limit,
            "total_pages": (total_records + limit - 1) // limit,
            "data": [_row_to_dict(r) for r in rows],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Şikayetleriniz yüklenemedi: {str(e)}")


@router.get("/api/admin/reports")
async def get_reports(page: int = 1, limit: int = 50, status: Optional[str] = None, user: dict = Depends(require_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        offset = (page - 1) * limit
        if status and status != "all":
            cursor.execute("SELECT COUNT(*) FROM reports WHERE status = %s", (status,))
            total_records = cursor.fetchone()[0]
            cursor.execute(
                "SELECT id, user_email, news_query, news_details, report_reason, admin_response, status, source_id, created_at, updated_at FROM reports WHERE status = %s ORDER BY id DESC LIMIT %s OFFSET %s",
                (status, limit, offset),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM reports")
            total_records = cursor.fetchone()[0]
            cursor.execute(
                "SELECT id, user_email, news_query, news_details, report_reason, admin_response, status, source_id, created_at, updated_at FROM reports ORDER BY id DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
        rows = cursor.fetchall()
        conn.close()
        return {
            "total": total_records, "page": page, "limit": limit,
            "total_pages": (total_records + limit - 1) // limit,
            "data": [_row_to_dict(r) for r in rows],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Şikayetler yüklenemedi: {str(e)}")


@router.post("/api/admin/reports/{report_id}/respond")
async def respond_report(report_id: int, request: ReportResponseRequest, user: dict = Depends(require_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Şikayet kaydı bulunamadı.")
        cursor.execute(
            "UPDATE reports SET admin_response = %s, status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (request.admin_response, request.status, report_id),
        )
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Şikayet başarıyla güncellendi."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"], "user_email": row["user_email"], "news_query": row["news_query"],
        "news_details": row["news_details"], "report_reason": row["report_reason"],
        "admin_response": row["admin_response"], "status": row["status"],
        "source_id": row["source_id"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }

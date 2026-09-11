"""
Auth Router — Kayıt, doğrulama, giriş endpoint'leri.
"""
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

from src.backend.auth import (
    get_db_connection, get_password_hash, verify_password,
    create_access_token, generate_verification_code, send_verification_email,
    SECRET_KEY, ALGORITHM,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# ---- Pydantic Modeller ----

class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str


class VerifyRequest(BaseModel):
    email: str
    code: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ---- Bağımlılıklar ----

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token gerekli")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        first_name: str = payload.get("first_name", "")
        last_name: str = payload.get("last_name", "")
        if email is None:
            raise HTTPException(status_code=401, detail="Geçersiz token")
        return {"email": email, "role": role, "first_name": first_name, "last_name": last_name}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token süresi dolmuş")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Geçersiz token")


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Yalnızca admin yetkisine sahip kullanıcılar erişebilir")
    return current_user


# ---- Endpoint'ler ----

@router.post("/register")
async def register_user(request: RegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (request.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")

    code = generate_verification_code()
    hashed_pw = get_password_hash(request.password)
    cursor.execute(
        "INSERT INTO users (email, password_hash, is_verified, verify_code, first_name, last_name) VALUES (%s, %s, False, %s, %s, %s)",
        (request.email, hashed_pw, code, request.first_name, request.last_name),
    )
    conn.commit()
    conn.close()
    send_verification_email(request.email, code)
    return {"status": "success", "message": "Kayıt başarılı. Lütfen email adresinize gelen kodu girin."}


@router.post("/verify")
async def verify_user(request: VerifyRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s AND verify_code = %s", (request.email, request.code))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Geçersiz doğrulama kodu veya email.")
    cursor.execute("UPDATE users SET is_verified = True, verify_code = NULL WHERE email = %s", (request.email,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Hesabınız başarıyla doğrulandı. Giriş yapabilirsiniz."}


@router.post("/login")
async def login_user(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (request.email,))
    user = cursor.fetchone()
    conn.close()
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Geçersiz email veya şifre.")
    if not user["is_verified"]:
        raise HTTPException(status_code=403, detail="Lütfen önce email adresinizi doğrulayın.")
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"], "first_name": user["first_name"], "last_name": user["last_name"]}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
    }

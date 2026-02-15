import hashlib
import hmac
import time
from fastapi import Request, HTTPException, Response
from app.config import TEACHER_PASSWORD_HASH, APP_SECRET_KEY, SESSION_EXPIRY_DAYS

COOKIE_NAME = "kapp_session"


def verify_teacher_password(password: str) -> bool:
    import bcrypt
    if not TEACHER_PASSWORD_HASH:
        return False
    try:
        return bcrypt.checkpw(password.encode(), TEACHER_PASSWORD_HASH.encode())
    except Exception:
        return False


def create_session_token(role: str = "student", student_id: int = 0) -> str:
    expires = int(time.time()) + SESSION_EXPIRY_DAYS * 86400
    payload = f"{expires}.{role}.{student_id}"
    sig = hmac.new(APP_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_session_token(token: str) -> tuple[bool, str, int]:
    """Returns (valid, role, student_id) tuple."""
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return False, "", 0
        payload, sig = parts
        expected = hmac.new(APP_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False, "", 0
        payload_parts = payload.split(".")
        expires = int(payload_parts[0])
        role = payload_parts[1] if len(payload_parts) > 1 else "student"
        student_id = int(payload_parts[2]) if len(payload_parts) > 2 else 0
        if time.time() >= expires:
            return False, "", 0
        return True, role, student_id
    except Exception:
        return False, "", 0


def get_session_info(request: Request) -> tuple[str, int]:
    """Extract role and student_id from session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return "", 0
    valid, role, student_id = verify_session_token(token)
    return (role, student_id) if valid else ("", 0)


def get_student_id(request: Request) -> int:
    """Extract student_id from session. Returns 0 for teacher or invalid."""
    _, student_id = get_session_info(request)
    return student_id


def set_session_cookie(response: Response, role: str = "student", student_id: int = 0) -> Response:
    token = create_session_token(role, student_id)
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=SESSION_EXPIRY_DAYS * 86400,
        httponly=True, samesite="lax", secure=False
    )
    return response


def require_auth(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    valid, role, student_id = verify_session_token(token)
    if not valid:
        raise HTTPException(status_code=401, detail="Not authenticated")


def require_teacher(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    valid, role, student_id = verify_session_token(token)
    if not valid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")

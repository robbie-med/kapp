from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.config import BASE_DIR, AUDIO_PATH
from app.database import init_db, get_db
from app.auth import require_auth, require_teacher, verify_teacher_password, set_session_cookie, get_session_info, COOKIE_NAME
from app.models import LoginRequest, StudentLoginRequest, StudentCreate


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logging.basicConfig(level=logging.INFO)
    await init_db()
    AUDIO_PATH.mkdir(parents=True, exist_ok=True)
    from app.bots.telegram_bot import start_telegram_bot, stop_telegram_bot
    await start_telegram_bot()
    yield
    await stop_telegram_bot()


app = FastAPI(title="Korean Learning App", lifespan=lifespan)


# --- Auth routes (public) ---

@app.post("/api/login")
async def login(req: StudentLoginRequest):
    import bcrypt
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, password_hash FROM students WHERE username = ?",
            (req.username,)
        )
        if not rows:
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
        student_id, pw_hash = rows[0][0], rows[0][1]
        if not pw_hash or not bcrypt.checkpw(req.password.encode(), pw_hash.encode()):
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
        resp = JSONResponse({"ok": True, "role": "student", "student_id": student_id})
        set_session_cookie(resp, role="student", student_id=student_id)
        return resp
    finally:
        await db.close()


@app.post("/api/login/teacher")
async def login_teacher(req: LoginRequest):
    if not verify_teacher_password(req.password):
        return JSONResponse({"error": "Wrong password"}, status_code=401)
    resp = JSONResponse({"ok": True, "role": "teacher"})
    set_session_cookie(resp, role="teacher", student_id=0)
    return resp


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/api/auth/check")
async def auth_check(request: Request):
    role, student_id = get_session_info(request)
    if role:
        result = {"authenticated": True, "role": role}
        if role == "student" and student_id:
            db = await get_db()
            try:
                rows = await db.execute_fetchall(
                    "SELECT username, display_name FROM students WHERE id = ?", (student_id,)
                )
                if rows:
                    result["student_id"] = student_id
                    result["username"] = rows[0][0]
                    result["display_name"] = rows[0][1]
            finally:
                await db.close()
        return result
    return JSONResponse({"authenticated": False}, status_code=401)


# --- Health check ---

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Student management (teacher only) ---

@app.get("/api/students", dependencies=[Depends(require_teacher)])
async def list_students():
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, username, display_name, created_at FROM students ORDER BY id"
        )
        return {"students": [{"id": r[0], "username": r[1], "display_name": r[2], "created_at": r[3]} for r in rows]}
    finally:
        await db.close()


@app.post("/api/students", dependencies=[Depends(require_teacher)])
async def create_student(req: StudentCreate):
    import bcrypt
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO students (username, display_name, password_hash) VALUES (?, ?, ?)",
            (req.username, req.display_name, pw_hash)
        )
        await db.commit()
        return {"id": cursor.lastrowid, "username": req.username}
    except Exception as e:
        if "UNIQUE" in str(e):
            return JSONResponse({"error": "Username already exists"}, status_code=409)
        raise
    finally:
        await db.close()


@app.delete("/api/students/{student_id}", dependencies=[Depends(require_teacher)])
async def delete_student(student_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM students WHERE id = ?", (student_id,))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


# --- Import routers (all require auth) ---

from app.routers import practice, items, review, stats, settings, webhook, sentences, goals, curriculum

app.include_router(practice.router, prefix="/api/practice", dependencies=[Depends(require_auth)])
app.include_router(items.router, prefix="/api/items", dependencies=[Depends(require_auth)])
app.include_router(review.router, prefix="/api/review", dependencies=[Depends(require_auth)])
app.include_router(stats.router, prefix="/api/stats", dependencies=[Depends(require_auth)])
app.include_router(settings.router, prefix="/api/settings", dependencies=[Depends(require_auth)])
app.include_router(sentences.router, prefix="/api/sentences", dependencies=[Depends(require_auth)])
app.include_router(goals.router, prefix="/api/goals", dependencies=[Depends(require_auth)])
app.include_router(curriculum.router, prefix="/api/curriculum", dependencies=[Depends(require_auth)])
app.include_router(webhook.router, prefix="/api/webhook")  # webhooks auth differently


# --- Static files ---

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/{path:path}")
async def serve_spa(path: str):
    """Serve index.html for all non-API routes (SPA)."""
    file_path = BASE_DIR / "static" / path
    if path and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(BASE_DIR / "static" / "index.html")

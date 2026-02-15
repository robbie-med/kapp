from fastapi import APIRouter, Request
from app.database import get_db
from app.models import SettingUpdate
from app.auth import get_student_id

router = APIRouter()

DEFAULTS = {
    "default_formality": "polite",
    "default_topik_level": "1",
    "items_per_session": "3",
    "auto_play_prompt": "true",
    "new_items_per_session": "2",
    "curriculum_enabled": "true",
}

SENSITIVE_KEYS = {"openai_api_key", "telegram_bot_token"}

# Bot config keys: (env_var_name, is_sensitive)
BOT_CONFIG_KEYS = {
    "telegram_bot_token": ("TELEGRAM_BOT_TOKEN", True),
    "telegram_teacher_id": ("TELEGRAM_TEACHER_ID", False),
    "signal_api_url": ("SIGNAL_API_URL", False),
    "signal_phone_number": ("SIGNAL_PHONE_NUMBER", False),
    "signal_teacher_number": ("SIGNAL_TEACHER_NUMBER", False),
}


def _mask_key(value: str) -> str:
    if not value or len(value) < 8:
        return "••••" if value else ""
    return value[:3] + "•" * (len(value) - 7) + value[-4:]


@router.get("")
async def get_settings(request: Request):
    student_id = get_student_id(request) or 0
    db = await get_db()
    try:
        # Get global settings + student-specific overrides
        rows = await db.execute_fetchall("SELECT key, value FROM settings WHERE student_id = 0")
        if student_id:
            student_rows = await db.execute_fetchall(
                "SELECT key, value FROM settings WHERE student_id = ?", (student_id,)
            )
        else:
            student_rows = []
        settings = dict(DEFAULTS)
        for r in rows:
            if r[0] in SENSITIVE_KEYS:
                settings[r[0]] = _mask_key(r[1])
                settings[f"{r[0]}_set"] = bool(r[1])
            else:
                settings[r[0]] = r[1]
        # Student-specific settings override globals
        for r in student_rows:
            if r[0] in SENSITIVE_KEYS:
                settings[r[0]] = _mask_key(r[1])
                settings[f"{r[0]}_set"] = bool(r[1])
            else:
                settings[r[0]] = r[1]

        # OpenAI key .env fallback
        if "openai_api_key" not in settings:
            from app.config import OPENAI_API_KEY
            if OPENAI_API_KEY and OPENAI_API_KEY != "sk-...":
                settings["openai_api_key"] = _mask_key(OPENAI_API_KEY)
                settings["openai_api_key_set"] = True
            else:
                settings["openai_api_key"] = ""
                settings["openai_api_key_set"] = False

        # Bot config .env fallbacks
        import app.config as cfg
        for key, (env_attr, is_sensitive) in BOT_CONFIG_KEYS.items():
            if key not in settings:
                env_val = getattr(cfg, env_attr, "")
                if is_sensitive:
                    settings[key] = _mask_key(env_val) if env_val else ""
                    settings[f"{key}_set"] = bool(env_val)
                else:
                    settings[key] = env_val or ""

        return settings
    finally:
        await db.close()


@router.put("/{key}")
async def update_setting(key: str, body: SettingUpdate, request: Request):
    student_id = get_student_id(request) or 0
    # Bot config keys are always global (student_id=0)
    if key in BOT_CONFIG_KEYS or key in ("openai_api_key",):
        student_id = 0
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value, student_id) VALUES (?, ?, ?)",
            (key, body.value, student_id)
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.post("/openai-key/test")
async def test_openai_key():
    """Test that the current OpenAI key works."""
    try:
        from app.services.openai_service import _get_client
        client = await _get_client()
        await client.models.list()
        return {"ok": True, "message": "API key is valid"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@router.get("/bots/status")
async def get_bot_status():
    """Get running status of bot integrations."""
    from app.bots.telegram_bot import get_telegram_status
    return {
        "telegram": get_telegram_status(),
    }


@router.post("/telegram/restart")
async def restart_telegram():
    """Restart the Telegram bot with current config."""
    try:
        from app.bots.telegram_bot import restart_telegram_bot, get_telegram_status
        await restart_telegram_bot()
        return {"ok": True, **get_telegram_status()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/signal/test")
async def test_signal():
    """Test Signal connectivity by hitting the signal-cli-rest-api."""
    import httpx
    from app.database import get_setting
    from app.config import SIGNAL_API_URL
    api_url = await get_setting("signal_api_url", SIGNAL_API_URL)
    if not api_url:
        return {"ok": False, "message": "No Signal API URL configured"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{api_url}/v1/about")
            if resp.status_code == 200:
                return {"ok": True, "message": "Signal API is reachable"}
            return {"ok": False, "message": f"Signal API returned {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

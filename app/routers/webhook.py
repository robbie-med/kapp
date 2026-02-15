from fastapi import APIRouter, Request
from app.config import SIGNAL_TEACHER_NUMBER as _ENV_TEACHER_NUM
from app.database import get_setting
from app.services.message_parser import process_teacher_items

router = APIRouter()


@router.post("/signal")
async def signal_webhook(request: Request):
    """Receive messages from signal-cli-rest-api."""
    data = await request.json()
    envelope = data.get("envelope", {})
    source = envelope.get("source", "")
    message = envelope.get("dataMessage", {}).get("message", "")

    teacher_number = await get_setting("signal_teacher_number", _ENV_TEACHER_NUM)
    if not message or source != teacher_number:
        return {"ok": True, "processed": False}

    result = await process_teacher_items(message, source="signal")
    return {
        "ok": True,
        "processed": True,
        "created_ids": result["created_ids"],
        "message": result["message"],
    }

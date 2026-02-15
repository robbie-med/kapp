"""Signal bot integration via signal-cli-rest-api."""

import logging
import httpx
from app.config import SIGNAL_API_URL as _ENV_API_URL, SIGNAL_PHONE_NUMBER as _ENV_PHONE
from app.database import get_setting

logger = logging.getLogger(__name__)


async def _get_signal_config():
    api_url = await get_setting("signal_api_url", _ENV_API_URL)
    phone = await get_setting("signal_phone_number", _ENV_PHONE)
    return api_url, phone


async def send_signal_message(recipient: str, message: str):
    """Send a message via Signal."""
    api_url, phone = await _get_signal_config()
    if not api_url or not phone:
        logger.warning("Signal not configured")
        return

    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{api_url}/v2/send",
                json={
                    "message": message,
                    "number": phone,
                    "recipients": [recipient],
                }
            )
        except Exception as e:
            logger.error(f"Failed to send Signal message: {e}")

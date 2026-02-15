import openai
from app.config import OPENAI_API_KEY


async def _get_api_key() -> str:
    """Get API key from DB settings first, fall back to .env."""
    try:
        from app.database import get_db
        db = await get_db()
        try:
            rows = await db.execute_fetchall(
                "SELECT value FROM settings WHERE key = 'openai_api_key'"
            )
            if rows and rows[0][0]:
                return rows[0][0]
        finally:
            await db.close()
    except Exception:
        pass
    return OPENAI_API_KEY


async def _get_client() -> openai.AsyncOpenAI:
    key = await _get_api_key()
    return openai.AsyncOpenAI(api_key=key)


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe Korean audio using Whisper API."""
    client = await _get_client()
    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, audio_bytes),
        language="ko",
    )
    return response.text


async def chat_completion(system_prompt: str, user_prompt: str,
                          response_format: dict | None = None) -> str:
    """Call GPT-4o with given prompts."""
    client = await _get_client()
    kwargs = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }
    if response_format:
        kwargs["response_format"] = response_format
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

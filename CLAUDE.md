# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (from project root, with venv activated)
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8100

# Seed the database (only works on empty DB; delete data/korean_app.db to re-seed)
python scripts/seed_db.py

# Signal bot (docker-compose runs signal-cli-rest-api on localhost:8101)
docker-compose up -d

# Production: systemd service at deploy/korean-app.service, nginx config at deploy/nginx-korean-app
```

## Architecture

**Backend**: FastAPI app (`app/main.py`) using async aiosqlite for a single-file SQLite database (`data/korean_app.db`). No ORM — raw SQL with `aiosqlite.Row` row factory. Database schema is defined inline in `app/database.py`. Each request creates its own `get_db()` connection (no connection pool).

**Auth**: Single-password auth with bcrypt. Session tokens are HMAC-signed expiry timestamps stored in a cookie (`kapp_session`). All `/api/*` routers except `/api/webhook` require auth via `Depends(require_auth)`.

**AI pipeline** (all via OpenAI API, `app/services/openai_service.py`):
- `prompt_generator.py` — GPT-4o generates Korean practice prompts from target vocab/grammar items
- `correction.py` — Whisper transcribes student audio, then GPT-4o scores grammar/vocab/formality and returns structured JSON feedback
- `message_parser.py` — Parses teacher messages: regex patterns first, GPT-4o fallback for natural language

The OpenAI API key can come from either the `.env` file or the `settings` DB table (DB takes priority, checked in `_get_api_key()`).

**SRS**: Modified SM-2 algorithm in `app/services/srs.py`. Sub-scores (grammar, vocab, formality) act as weakness multipliers that shorten review intervals for weak areas. Mastery scores are rolling averages updated per practice attempt.

**Item ingestion**: A teacher adds vocab/grammar via Telegram bot (long-polling, started in app lifespan) or Signal webhook (`/api/webhook/signal`, receives from signal-cli-rest-api container). Both use `message_parser.py` and `database.insert_item()`.

**Frontend**: Vanilla JS SPA served from `static/`. `index.html` is the shell; page modules in `static/js/pages/` handle routing. PWA-capable (service worker + manifest).

## Key Patterns

- Pydantic models in `app/models.py` are request/response schemas only — not DB models.
- JSON arrays are stored as TEXT in SQLite (e.g., `tags`, `item_ids`), serialized via `json.dumps`/`json.loads`.
- All AI service calls return JSON strings that are `json.loads`'d by the caller; they use `response_format={"type": "json_object"}`.
- Config is env-var based via `app/config.py` (loaded from `.env` by python-dotenv). All paths are resolved relative to `BASE_DIR` (project root).

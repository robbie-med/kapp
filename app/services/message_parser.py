"""Parse teacher messages from Telegram/Signal into structured vocab/grammar items."""

import re
import json
import logging
from app.services.openai_service import chat_completion
from app.database import (
    get_db, get_setting, set_setting, insert_item,
    check_duplicate_item, delete_items_by_ids,
)

logger = logging.getLogger(__name__)

# --- Command parsing ---

COMMAND_PATTERNS = {
    "set_level": re.compile(r'^/(?:level|topik)\s+(\d)$', re.IGNORECASE),
    "set_tags": re.compile(r'^/tags\s+(.+)$', re.IGNORECASE),
    "status": re.compile(r'^/status$', re.IGNORECASE),
    "undo": re.compile(r'^/undo$', re.IGNORECASE),
}


def parse_command(message: str) -> dict | None:
    """Check if message is a teacher command. Returns command dict or None."""
    msg = message.strip()
    for cmd_name, pattern in COMMAND_PATTERNS.items():
        m = pattern.match(msg)
        if not m:
            continue
        if cmd_name == "set_level":
            return {"command": "set_level", "value": int(m.group(1))}
        elif cmd_name == "set_tags":
            raw = m.group(1).strip()
            if raw.lower() == "clear":
                return {"command": "clear_tags"}
            tags = [t.strip().lstrip("#") for t in raw.split(",") if t.strip()]
            return {"command": "set_tags", "value": tags}
        else:
            return {"command": cmd_name}
    return None


# --- Item parsing ---

# Regex patterns for common teacher message formats
# Updated to support optional T3:/L3: level prefix and #tag suffixes
ITEM_PATTERN = re.compile(
    r'^'
    r'(?:(?:T|L)(\d)\s*[:：]\s*)?'        # optional level prefix: T3: or L3:
    r'(?:(?:새\s*단어|문법|vocab|grammar)\s*[:：]\s*)?'  # optional type prefix
    r'([가-힣~\-][가-힣\s\-~/()\u3130-\u318F]+?)'  # korean text (required)
    r'\s*[-–—]\s*'                          # separator dash
    r'(.+?)'                                # english meaning
    r'((?:\s+#\w+)*)'                       # optional #tag suffixes
    r'\s*$',
    re.MULTILINE
)

# Simple POS inference for regex-matched items
POS_HINTS = {
    "하다": "verb", "되다": "verb", "가다": "verb", "오다": "verb",
    "이다": "adjective", "있다": "adjective", "없다": "adjective",
}

GPT_PARSE_PROMPT = """You are a Korean language teaching assistant. Extract vocabulary and grammar items from the teacher's message.

{context_hint}

Return JSON:
{{
  "items": [
    {{
      "korean": "the Korean word/pattern",
      "english": "English meaning",
      "item_type": "vocab" or "grammar",
      "topik_level": estimated 1-6,
      "tags": ["relevant", "category", "tags"],
      "notes": "any extra context from the message",
      "pos": "noun/verb/adjective/adverb/particle/determiner/interjection/suffix" (for vocab only, null for grammar),
      "dictionary_form": "the dictionary/base form if different from korean field, else null",
      "grammar_category": "ending/particle/connector/expression/conjugation" (for grammar only, null for vocab)
    }}
  ]
}}

If the message doesn't contain any Korean learning content, return {{"items": []}}."""


def _infer_pos(korean: str, item_type: str) -> str | None:
    """Simple POS inference for regex-matched vocab items."""
    if item_type != "vocab":
        return None
    for suffix, pos in POS_HINTS.items():
        if korean.endswith(suffix):
            return pos
    if korean[-1] in "음성기도":
        return "noun"
    return None


def _infer_grammar_category(korean: str, item_type: str) -> str | None:
    """Simple grammar category inference for regex-matched grammar items."""
    if item_type != "grammar":
        return None
    if korean.startswith("-") or korean.startswith("~"):
        return "ending"
    return None


def _extract_inline_tags(tag_str: str) -> list[str]:
    """Extract tags from '#food #daily' style suffix."""
    if not tag_str or not tag_str.strip():
        return []
    return [t.lstrip("#") for t in tag_str.split() if t.startswith("#") and len(t) > 1]


async def parse_teacher_message(message: str, context: dict | None = None) -> list[dict]:
    """Parse a teacher's message into structured items. Try regex first, fall back to GPT."""
    ctx = context or {}
    default_level = ctx.get("default_level", 1)
    default_tags = ctx.get("default_tags", [])

    items = []

    for m in ITEM_PATTERN.finditer(message):
        level_str, korean, english, tags_str = m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4)

        # Determine item type
        type_hint = message[:m.start()].lower()
        if "문법" in type_hint or "grammar" in type_hint or korean.startswith(("-", "~")):
            item_type = "grammar"
        else:
            item_type = "vocab"

        # Level: inline override > context default
        topik_level = int(level_str) if level_str else default_level

        # Tags: inline tags + context defaults (deduplicated)
        inline_tags = _extract_inline_tags(tags_str)
        # Strip any trailing #tags from english text
        english = re.sub(r'\s+#\w+', '', english).strip()
        merged_tags = list(dict.fromkeys(default_tags + inline_tags))

        items.append({
            "korean": korean,
            "english": english,
            "item_type": item_type,
            "topik_level": topik_level,
            "tags": merged_tags,
            "notes": "",
            "pos": _infer_pos(korean, item_type),
            "dictionary_form": None,
            "grammar_category": _infer_grammar_category(korean, item_type),
        })

    if items:
        return items

    # Fall back to GPT-4o parsing with context hint
    context_hint = ""
    if default_level > 1:
        context_hint = f"The teacher is currently adding TOPIK level {default_level} items. Use this as the default level unless the content clearly suggests otherwise."
    if default_tags:
        context_hint += f" Default tags to include: {', '.join(default_tags)}."

    prompt = GPT_PARSE_PROMPT.format(context_hint=context_hint or "No additional context.")
    result = await chat_completion(
        prompt, message,
        response_format={"type": "json_object"}
    )
    parsed = json.loads(result)
    gpt_items = parsed.get("items", [])

    # Merge default tags into GPT results too
    if default_tags:
        for item in gpt_items:
            existing = item.get("tags", [])
            item["tags"] = list(dict.fromkeys(default_tags + existing))

    return gpt_items


# --- Shared processing (used by both Telegram bot and Signal webhook) ---

async def _load_teacher_context() -> dict:
    """Load sticky teacher context from settings."""
    level_str = await get_setting("teacher_default_level", "1")
    tags_str = await get_setting("teacher_default_tags", "")
    return {
        "default_level": int(level_str) if level_str.isdigit() else 1,
        "default_tags": [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else [],
    }


async def _handle_command(cmd: dict) -> str:
    """Execute a teacher command and return response message."""
    command = cmd["command"]

    if command == "set_level":
        level = cmd["value"]
        if not 1 <= level <= 6:
            return "Level must be between 1 and 6."
        await set_setting("teacher_default_level", str(level))
        return f"Default level set to TOPIK {level}"

    elif command == "set_tags":
        tags = cmd["value"]
        await set_setting("teacher_default_tags", ",".join(tags))
        return f"Default tags: {', '.join(tags)}"

    elif command == "clear_tags":
        await set_setting("teacher_default_tags", "")
        return "Default tags cleared."

    elif command == "status":
        ctx = await _load_teacher_context()
        level = ctx["default_level"]
        tags = ctx["default_tags"]
        parts = [f"TOPIK level: {level}"]
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")
        else:
            parts.append("Tags: (none)")
        # Load last batch info
        last_batch = await get_setting("teacher_last_batch_ids", "")
        if last_batch:
            count = len(last_batch.split(","))
            parts.append(f"Last batch: {count} item(s) (use /undo to remove)")
        return "Current context:\n" + "\n".join(parts)

    elif command == "undo":
        last_batch = await get_setting("teacher_last_batch_ids", "")
        if not last_batch:
            return "Nothing to undo."
        item_ids = [int(x) for x in last_batch.split(",") if x.strip()]
        db = await get_db()
        try:
            deleted = await delete_items_by_ids(db, item_ids)
            await db.commit()
            await set_setting("teacher_last_batch_ids", "")
            return f"Undone: deleted {deleted} item(s) from last batch."
        finally:
            await db.close()

    return "Unknown command."


def _format_item_line(item: dict, item_id: int) -> str:
    """Format a single item for the confirmation message."""
    icon = "\U0001f4d8" if item["item_type"] == "grammar" else "\U0001f4d7"
    tags_str = " ".join(f"#{t}" for t in item.get("tags", []))
    parts = [
        f"  {icon} {item['korean']} \u2192 {item['english']}",
        f"(T{item.get('topik_level', 1)}, {item['item_type']})",
    ]
    line = " ".join(parts)
    if tags_str:
        line += f" {tags_str}"
    return line


async def process_teacher_items(message: str, source: str = "telegram") -> dict:
    """Process a teacher message: handle commands or parse+insert items.

    Returns {"message": str, "created_ids": list[int], "is_command": bool}
    """
    # 1. Check for commands
    cmd = parse_command(message)
    if cmd:
        reply = await _handle_command(cmd)
        return {"message": reply, "created_ids": [], "is_command": True}

    # 2. Load sticky context
    ctx = await _load_teacher_context()

    # 3. Parse items
    parsed_items = await parse_teacher_message(message, context=ctx)
    if not parsed_items:
        return {
            "message": "I couldn't find any vocabulary or grammar items in that message. Try:\n"
                       "\u2022 \ud589\ubcf5\ud558\ub2e4 - to be happy\n"
                       "\u2022 T3: \ud589\ubcf5\ud558\ub2e4 - to be happy\n"
                       "\u2022 /level 3 (set default TOPIK level)\n"
                       "\u2022 /tags food (set default tags)\n"
                       "\u2022 /status (show current context)",
            "created_ids": [],
            "is_command": False,
        }

    # 4. Check duplicates and insert
    db = await get_db()
    try:
        created = []
        duplicates = []
        for item in parsed_items:
            dup = await check_duplicate_item(db, item["korean"])
            if dup:
                duplicates.append(dup)
                continue

            item_id = await insert_item(
                db, item["korean"], item["english"],
                item.get("item_type", "vocab"),
                item.get("topik_level", 1),
                source=source,
                tags=item.get("tags", []),
                notes=item.get("notes", ""),
                pos=item.get("pos"),
                dictionary_form=item.get("dictionary_form"),
                grammar_category=item.get("grammar_category"),
            )
            created.append({"item": item, "id": item_id})

        await db.commit()

        # 5. Save last batch IDs for undo
        if created:
            batch_ids = ",".join(str(c["id"]) for c in created)
            await set_setting("teacher_last_batch_ids", batch_ids)

        # 6. Build reply
        lines = []
        if created:
            lines.append(f"Added {len(created)} item(s):")
            for c in created:
                lines.append(_format_item_line(c["item"], c["id"]))

        if duplicates:
            dup_parts = [f"{d['korean']} (#{d['id']})" for d in duplicates]
            lines.append(f"\u26a0\ufe0f Skipped {len(duplicates)} duplicate(s): {', '.join(dup_parts)}")

        if not created and not duplicates:
            lines.append("No items were added.")

        # Show context if non-default
        ctx_parts = []
        if ctx["default_level"] > 1:
            ctx_parts.append(f"TOPIK {ctx['default_level']}")
        if ctx["default_tags"]:
            ctx_parts.append(f"tags: {', '.join(ctx['default_tags'])}")
        if ctx_parts:
            lines.append(f"Context: {', '.join(ctx_parts)}")

        return {
            "message": "\n".join(lines),
            "created_ids": [c["id"] for c in created],
            "is_command": False,
        }
    finally:
        await db.close()

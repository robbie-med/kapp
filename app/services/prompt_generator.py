"""Generate practice prompts using GPT-4o."""

import json
from app.services.openai_service import chat_completion

SYSTEM_PROMPT = """You are a Korean language practice prompt generator.
Given a list of Korean vocabulary/grammar items and a formality level, create a short,
realistic situational prompt that naturally requires the student to use those items.

Some items may include example sentences provided by the teacher. Use these examples
as inspiration for the kind of context or usage the teacher wants the student to practice,
but create an original situation — do not simply repeat the examples.

Return JSON with exactly these fields:
{
  "prompt": "The situation description in Korean (1-2 sentences)",
  "prompt_english": "English translation of the situation"
}

Guidelines:
- The situation should be natural and everyday (ordering food, asking directions, etc.)
- Make it clear what formality level to use
- The student should need to produce 1-3 sentences using the target items
- Keep it focused - don't require too many items at once"""


async def generate_prompt(items: list[dict], formality: str, db=None) -> dict:
    """Generate practice prompt using GPT-4o. If db provided, store as sentence with auto-linking."""
    items_desc_parts = []
    for item in items:
        line = f"- {item['korean']} ({item['english']})"
        examples = item.get("examples", [])
        if examples:
            for ex in examples:
                formality_label = ex.get("formality", "")
                line += f"\n  예문: {ex['korean']} ({ex['english']}) [{formality_label}]"
        items_desc_parts.append(line)

    items_desc = "\n".join(items_desc_parts)

    formality_desc = {
        "formal": "합쇼체 (formal/deferential - e.g., -(스)ㅂ니다)",
        "polite": "해요체 (polite - e.g., -아/어요)",
        "casual": "해체 (casual - e.g., -아/어)",
    }.get(formality, "해요체 (polite)")

    user_msg = f"""Target items:
{items_desc}

Formality level: {formality_desc}

Generate a practice prompt that requires using these items."""

    result = await chat_completion(
        SYSTEM_PROMPT, user_msg,
        response_format={"type": "json_object"}
    )
    prompt_data = json.loads(result)

    # Store as sentence if db provided
    if db:
        from app.database import find_matching_items, insert_sentence

        matched_items = await find_matching_items(db, prompt_data["prompt"])
        linked_ids = [m["id"] for m in matched_items]

        # Calculate TOPIK level from linked items
        topik_level = max([m.get("topik_level", 1) for m in matched_items], default=1)

        sentence_id = await insert_sentence(
            db, prompt_data["prompt"], prompt_data["prompt_english"],
            formality, topik_level, source="ai_generated",
            linked_item_ids=linked_ids
        )
        prompt_data["sentence_id"] = sentence_id
        prompt_data["source"] = "ai_generated"

    return prompt_data


async def generate_prompt_with_sentences(items: list[dict], formality: str, db=None) -> dict:
    """Try to find a teacher sentence matching the items. Fall back to GPT generation."""
    if db:
        from app.database import get_sentences_for_items
        item_ids = [i["id"] for i in items]
        sentences = await get_sentences_for_items(db, item_ids)
        if sentences:
            # Pick the sentence with most matching items (already ordered by match_count DESC)
            best = sentences[0]
            return {
                "prompt": best["korean"],
                "prompt_english": best["english"],
                "sentence_id": best["id"],
                "source": "teacher_sentence",
            }
    # Fallback to GPT generation - NOW PASS DB
    result = await generate_prompt(items, formality, db=db)
    if "sentence_id" not in result:
        result["sentence_id"] = None
    if "source" not in result:
        result["source"] = "ai_generated"
    return result


async def format_sentence_prompt(sentence: dict) -> dict:
    """Format a teacher sentence as a practice prompt for sentence repetition mode."""
    return {
        "prompt": sentence["korean"],
        "prompt_english": sentence["english"],
        "sentence_id": sentence["id"],
        "source": "sentence_practice",
        "instruction": "Listen and repeat this sentence:",
        "instruction_korean": "다음 문장을 듣고 따라 하세요:",
    }

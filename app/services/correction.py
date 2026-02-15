"""Core AI correction pipeline."""

import json
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.config import AUDIO_PATH
from app.database import get_db, record_encounter, calculate_student_level, record_encounter_with_type, update_item_metrics
from app.services.openai_service import transcribe_audio, chat_completion
from app.services.srs import update_srs_after_practice

CORRECTION_SYSTEM_PROMPT = """You are an expert Korean language teacher analyzing a student's spoken Korean.
You will receive:
1. The practice prompt (situation the student was responding to)
2. The expected formality level
3. The target vocabulary/grammar items they should use
4. Their transcribed speech

IMPORTANT: Identify and assess EVERY vocabulary word and grammar pattern the student actually used in their response, not just the target items.

Return JSON with exactly this structure:
{
  "overall_score": 0.0-1.0,
  "items_used": [
    {
      "korean": "어제",
      "english": "yesterday",
      "item_type": "vocab",
      "status": "correct|incorrect|wrong_form",
      "explanation": "Brief explanation of usage"
    }
  ],
  "grammar_used": [
    {
      "pattern": "-았/었어요",
      "english": "past tense polite ending",
      "status": "correct|incorrect|wrong_form",
      "explanation": "Brief explanation of usage"
    }
  ],
  "target_items_feedback": [
    {"item": "target item korean", "status": "used_correctly|used_incorrectly|not_used", "explanation": "..."}
  ],
  "formality": {
    "expected": "formal|polite|casual",
    "detected": "what you detected",
    "issues": ["list of specific formality issues, empty if correct"]
  },
  "corrected_sentence": "The corrected version of what they said",
  "natural_alternative": "A more natural way to say it",
  "explanation": "Brief overall feedback in English (2-3 sentences)"
}

Scoring guide:
- 1.0: Perfect or near-perfect
- 0.8-0.9: Minor issues only
- 0.6-0.7: Some errors but communicative
- 0.4-0.5: Significant errors
- 0.0-0.3: Major errors or mostly incorrect

For items_used: Include ALL vocabulary words (nouns, verbs in dictionary form, adjectives, adverbs).
For grammar_used: Include ALL grammar patterns (verb endings, particles, connectors, sentence structures).
Use dictionary forms for verbs/adjectives (e.g., "먹다" not "먹었어").

Be encouraging but honest. Point out specific issues with clear explanations."""


async def find_database_item_by_korean(db, korean_text: str, item_type: str = None) -> dict | None:
    """Find a database item by Korean text. Matches against korean field or dictionary_form."""
    if item_type:
        rows = await db.execute_fetchall(
            "SELECT id, korean, english, item_type, topik_level FROM items WHERE (korean = ? OR dictionary_form = ?) AND item_type = ?",
            (korean_text, korean_text, item_type)
        )
    else:
        rows = await db.execute_fetchall(
            "SELECT id, korean, english, item_type, topik_level FROM items WHERE korean = ? OR dictionary_form = ?",
            (korean_text, korean_text)
        )

    if rows:
        return {"id": rows[0][0], "korean": rows[0][1], "english": rows[0][2],
                "item_type": rows[0][3], "topik_level": rows[0][4]}
    return None


async def log_unknown_item(db, korean: str, english: str, item_type: str,
                           transcript: str, student_id: int):
    """Log an item that the student used but isn't in our database yet."""
    await db.execute(
        """INSERT INTO unknown_items (korean, english, item_type, example_usage, student_id, created_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))""",
        (korean, english, item_type, transcript, student_id)
    )


async def process_audio_submission(audio_file: UploadFile, item_ids: list[int],
                                    formality: str, prompt: str,
                                    student_id: int = 1,
                                    duration_seconds: int | None = None,
                                    practice_mode: str = "speaking",
                                    sentence_id: int | None = None) -> dict:
    """Full pipeline: save audio -> transcribe -> correct -> update SRS."""
    # Save audio
    audio_bytes = await audio_file.read()
    audio_id = str(uuid.uuid4())
    ext = audio_file.filename.split(".")[-1] if audio_file.filename and "." in audio_file.filename else "webm"
    audio_path = AUDIO_PATH / f"{audio_id}.{ext}"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(audio_bytes)

    # Transcribe
    transcript = await transcribe_audio(audio_bytes, audio_file.filename or "audio.webm")

    # Get target items from DB
    db = await get_db()
    try:
        placeholders = ",".join("?" * len(item_ids))
        rows = await db.execute_fetchall(
            f"SELECT id, korean, english, item_type FROM items WHERE id IN ({placeholders})",
            item_ids
        )
        target_items = [
            {"id": r[0], "korean": r[1], "english": r[2], "item_type": r[3]}
            for r in rows
        ]

        # Get AI correction
        items_desc = "\n".join(
            f"- {item['korean']} ({item['english']}) [{item['item_type']}]"
            for item in target_items
        )
        user_msg = f"""Practice prompt: {prompt}
Expected formality: {formality}

Target items:
{items_desc}

Student's transcribed speech:
{transcript}"""

        correction_raw = await chat_completion(
            CORRECTION_SYSTEM_PROMPT, user_msg,
            response_format={"type": "json_object"}
        )
        correction = json.loads(correction_raw)
        correction["transcript"] = transcript

        # Add backwards compatibility fields for UI
        if "grammar" not in correction and "grammar_used" in correction:
            correction["grammar"] = correction["grammar_used"]
        if "vocabulary" not in correction and "items_used" in correction:
            correction["vocabulary"] = [
                {"word": item["korean"], "status": item["status"], "explanation": item["explanation"]}
                for item in correction["items_used"]
            ]

        # Process ALL items the student actually used (comprehensive tracking)
        formality_score = 1.0 if not correction.get("formality", {}).get("issues") else 0.5
        items_to_update = {}  # {item_id: score}

        # Process vocabulary items used
        for vocab_item in correction.get("items_used", []):
            db_item = await find_database_item_by_korean(db, vocab_item["korean"], "vocab")
            if db_item:
                # Score based on status
                score = 1.0 if vocab_item["status"] == "correct" else (0.5 if vocab_item["status"] == "wrong_form" else 0.0)
                is_error = vocab_item["status"] in ("incorrect", "wrong_form")
                items_to_update[db_item["id"]] = {
                    "overall": score,
                    "vocab": score,
                    "grammar": 0.5,  # Neutral
                    "formality": formality_score,
                    "was_used": True,
                    "was_error": is_error,
                    "encounter_type": "used_incorrectly" if is_error else "used_correctly"
                }
            # TODO: Log unknown items for teacher review (needs unknown_items table)

        # Process grammar patterns used
        for grammar_item in correction.get("grammar_used", []):
            db_item = await find_database_item_by_korean(db, grammar_item["pattern"], "grammar")
            if db_item:
                # Score based on status
                score = 1.0 if grammar_item["status"] == "correct" else (0.5 if grammar_item["status"] == "wrong_form" else 0.0)
                is_error = grammar_item["status"] in ("incorrect", "wrong_form")
                items_to_update[db_item["id"]] = {
                    "overall": score,
                    "grammar": score,
                    "vocab": 0.5,  # Neutral
                    "formality": formality_score,
                    "was_used": True,
                    "was_error": is_error,
                    "encounter_type": "used_incorrectly" if is_error else "used_correctly"
                }
            # TODO: Log unknown items for teacher review

        # Ensure target items are included (even if student didn't use them)
        for target_item in target_items:
            if target_item["id"] not in items_to_update:
                # Student didn't use a target item - score as 0 (missing)
                items_to_update[target_item["id"]] = {
                    "overall": 0.0,
                    "grammar": 0.0 if target_item["item_type"] == "grammar" else 0.5,
                    "vocab": 0.0 if target_item["item_type"] == "vocab" else 0.5,
                    "formality": formality_score,
                    "was_used": False,
                    "was_error": False,
                    "encounter_type": "missing"
                }

        # Update SRS for ALL items (both used and target)
        for item_id, item_data in items_to_update.items():
            await update_srs_after_practice(
                db, item_id, item_data["overall"],
                {"grammar_score": item_data["grammar"], "vocab_score": item_data["vocab"], "formality_score": item_data["formality"]},
                student_id=student_id
            )
            # Record detailed encounter with type for weakness tracking
            await record_encounter_with_type(db, student_id, item_id, item_data["encounter_type"])
            # Update comprehensive metrics (exposure, usage, error counts)
            await update_item_metrics(db, student_id, item_id,
                                     was_used=item_data["was_used"],
                                     was_error=item_data["was_error"])

        # Recalculate student level after practice
        await calculate_student_level(db, student_id)

        # Log the practice session (include ALL items encountered, not just target items)
        all_item_ids = list(items_to_update.keys())
        await db.execute(
            """INSERT INTO practice_log
               (item_ids, prompt, formality, audio_path, transcript, overall_score, feedback_json,
                student_id, duration_seconds, practice_mode, sentence_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (json.dumps(all_item_ids), prompt, formality, str(audio_path),
             transcript, correction["overall_score"], json.dumps(correction), student_id,
             duration_seconds, practice_mode, sentence_id)
        )
        await db.commit()

        return correction
    finally:
        await db.close()

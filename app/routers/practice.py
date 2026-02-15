from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from app.database import get_db, record_encounter
from app.models import PracticeRequest
from app.services.srs import select_review_items
from app.services.prompt_generator import generate_prompt, generate_prompt_with_sentences, format_sentence_prompt
from app.services.correction import process_audio_submission
from app.auth import get_student_id
import json
import uuid

router = APIRouter()


@router.post("/start")
async def start_practice(req: PracticeRequest, request: Request):
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        # Route to appropriate practice mode
        if req.lesson_id:
            return await _start_lesson_practice(db, req, student_id)
        elif req.mode == "sentence" and req.sentence_id:
            return await _start_sentence_practice(db, req, student_id)
        elif req.mode == "reading":
            return await _start_reading_practice(db, req, student_id)
        else:
            # Default: speaking practice
            return await _start_speaking_practice(db, req, student_id)
    finally:
        await db.close()


async def _start_speaking_practice(db, req, student_id):
    """Start speaking practice with AI-generated or teacher sentence prompts."""
    from app.database import get_setting
    new_per_session = int(await get_setting("new_items_per_session", "2", student_id=student_id))

    items = await select_review_items(
        db, count=req.item_count, topik_level=req.topik_level,
        student_id=student_id, new_items_per_session=new_per_session
    )
    if not items:
        return JSONResponse({"error": "No items available for review"}, status_code=404)

    # Fetch example sentences for selected items
    item_ids = [i["id"] for i in items]
    if item_ids:
        placeholders = ",".join("?" for _ in item_ids)
        example_rows = await db.execute_fetchall(
            f"SELECT item_id, korean, english, formality FROM examples WHERE item_id IN ({placeholders})",
            item_ids
        )
        examples_by_item = {}
        for er in example_rows:
            examples_by_item.setdefault(er[0], []).append({
                "korean": er[1], "english": er[2], "formality": er[3]
            })
        for item in items:
            item["examples"] = examples_by_item.get(item["id"], [])

    # Record encounters (student saw these items)
    for item_id in item_ids:
        await record_encounter(db, student_id, item_id, practiced=False)
    await db.commit()

    # Try teacher sentence first, fall back to GPT
    prompt_data = await generate_prompt_with_sentences(items, req.formality, db=db)
    session_id = str(uuid.uuid4())

    from datetime import datetime
    return {
        "session_id": session_id,
        "prompt": prompt_data["prompt"],
        "prompt_english": prompt_data["prompt_english"],
        "formality": req.formality,
        "item_ids": [i["id"] for i in items],
        "target_items": [{"id": i["id"], "korean": i["korean"], "english": i["english"]} for i in items],
        "sentence_id": prompt_data.get("sentence_id"),
        "prompt_source": prompt_data.get("source", "ai_generated"),
        "mode": "speaking",
        "started_at": datetime.utcnow().isoformat(),
    }


async def _start_sentence_practice(db, req, student_id):
    """Start sentence repetition practice with a specific sentence."""
    rows = await db.execute_fetchall(
        "SELECT id, korean, english, formality, topik_level FROM sentences WHERE id = ?",
        (req.sentence_id,)
    )
    if not rows:
        return JSONResponse({"error": "Sentence not found"}, status_code=404)

    sentence = {"id": rows[0][0], "korean": rows[0][1], "english": rows[0][2],
                "formality": rows[0][3], "topik_level": rows[0][4]}

    # Get linked items
    linked = await db.execute_fetchall(
        """SELECT i.id, i.korean, i.english, i.item_type
           FROM sentence_items si JOIN items i ON i.id = si.item_id
           WHERE si.sentence_id = ?""",
        (req.sentence_id,)
    )
    item_ids = [r[0] for r in linked]
    target_items = [{"id": r[0], "korean": r[1], "english": r[2]} for r in linked]

    for item_id in item_ids:
        await record_encounter(db, student_id, item_id, practiced=False)
    await db.commit()

    prompt_data = await format_sentence_prompt(sentence)

    from datetime import datetime
    return {
        "session_id": str(uuid.uuid4()),
        "prompt": prompt_data["prompt"],
        "prompt_english": prompt_data["prompt_english"],
        "formality": sentence["formality"],
        "item_ids": item_ids,
        "target_items": target_items,
        "sentence_id": sentence["id"],
        "prompt_source": "sentence_practice",
        "mode": "sentence",
        "instruction": prompt_data.get("instruction", ""),
        "started_at": datetime.utcnow().isoformat(),
    }


async def _start_reading_practice(db, req, student_id):
    """Return a set of flashcards for passive review."""
    from app.database import get_sentences_for_items
    items = await select_review_items(
        db, count=req.item_count, topik_level=req.topik_level,
        student_id=student_id
    )
    if not items:
        return JSONResponse({"error": "No items available"}, status_code=404)

    # For each item, find a sentence if available
    cards = []
    for item in items:
        sentences = await get_sentences_for_items(db, [item["id"]])
        card = {
            "item_id": item["id"],
            "korean": item["korean"],
            "english": item["english"],
            "item_type": item["item_type"],
            "topik_level": item["topik_level"],
            "sentence": sentences[0] if sentences else None,
        }
        # Fetch examples for the item
        examples = await db.execute_fetchall(
            "SELECT korean, english, formality FROM examples WHERE item_id = ?",
            (item["id"],)
        )
        card["examples"] = [{"korean": e[0], "english": e[1], "formality": e[2]} for e in examples]
        cards.append(card)

    for item in items:
        await record_encounter(db, student_id, item["id"], practiced=False)
    await db.commit()

    from datetime import datetime
    return {
        "session_id": str(uuid.uuid4()),
        "mode": "reading",
        "cards": cards,
        "started_at": datetime.utcnow().isoformat(),
    }


async def _start_lesson_practice(db, req, student_id):
    """Start practice with items from a specific curriculum lesson."""
    from datetime import datetime

    # Get lesson info
    lesson_rows = await db.execute_fetchall(
        """SELECT l.id, l.lesson_number, l.title, u.unit_number
           FROM curriculum_lessons l
           JOIN curriculum_units u ON u.id = l.unit_id
           WHERE l.id = ?""",
        (req.lesson_id,)
    )

    if not lesson_rows:
        return JSONResponse({"error": "Lesson not found"}, status_code=404)

    lesson_id, lesson_num, lesson_title, unit_num = lesson_rows[0]

    # Get items from this lesson
    item_rows = await db.execute_fetchall(
        """SELECT i.id, i.korean, i.english, i.item_type, i.topik_level
           FROM lesson_items li
           JOIN items i ON i.id = li.item_id
           WHERE li.lesson_id = ?
           ORDER BY li.introduced_order
           LIMIT ?""",
        (lesson_id, req.item_count)
    )

    if not item_rows:
        return JSONResponse({"error": "No items in this lesson"}, status_code=404)

    items = [{"id": r[0], "korean": r[1], "english": r[2], "item_type": r[3], "topik_level": r[4]} for r in item_rows]
    item_ids = [i["id"] for i in items]

    # Get examples for these items
    placeholders = ",".join("?" for _ in item_ids)
    example_rows = await db.execute_fetchall(
        f"SELECT item_id, korean, english, formality FROM examples WHERE item_id IN ({placeholders})",
        item_ids
    )
    examples_by_item = {}
    for er in example_rows:
        examples_by_item.setdefault(er[0], []).append({"korean": er[1], "english": er[2], "formality": er[3]})
    for item in items:
        item["examples"] = examples_by_item.get(item["id"], [])

    # Record encounters
    for item_id in item_ids:
        await record_encounter(db, student_id, item_id, practiced=False)
    await db.commit()

    # Generate prompt
    prompt_data = await generate_prompt_with_sentences(items, req.formality, db=db)

    # Update lesson progress
    await db.execute(
        """INSERT INTO lesson_progress (student_id, lesson_id, status, started_at, practice_count)
           VALUES (?, ?, 'in_progress', datetime('now'), 1)
           ON CONFLICT(student_id, lesson_id) DO UPDATE SET
               status = 'in_progress',
               practice_count = practice_count + 1,
               last_practiced = datetime('now')""",
        (student_id, lesson_id)
    )
    await db.commit()

    return {
        "session_id": str(uuid.uuid4()),
        "prompt": prompt_data["prompt"],
        "prompt_english": prompt_data["prompt_english"],
        "formality": req.formality,
        "item_ids": item_ids,
        "target_items": [{"id": i["id"], "korean": i["korean"], "english": i["english"]} for i in items],
        "sentence_id": prompt_data.get("sentence_id"),
        "prompt_source": prompt_data.get("source", "ai_generated"),
        "mode": "lesson",
        "lesson_id": lesson_id,
        "lesson_info": f"Unit {unit_num} - Lesson {lesson_num}: {lesson_title}",
        "started_at": datetime.utcnow().isoformat(),
    }


@router.post("/submit")
async def submit_practice(
    request: Request,
    audio: UploadFile = File(...),
    session_data: str = Form(...)
):
    student_id = get_student_id(request) or 1
    session = json.loads(session_data)

    # Calculate duration
    duration_seconds = None
    started_at = session.get("started_at")
    if started_at:
        from datetime import datetime
        try:
            start = datetime.fromisoformat(started_at)
            duration_seconds = int((datetime.utcnow() - start).total_seconds())
        except (ValueError, TypeError):
            pass

    result = await process_audio_submission(
        audio_file=audio,
        item_ids=session["item_ids"],
        formality=session["formality"],
        prompt=session["prompt"],
        student_id=student_id,
        duration_seconds=duration_seconds,
        practice_mode=session.get("mode", "speaking"),
        sentence_id=session.get("sentence_id"),
    )
    return result


@router.post("/reading/complete")
async def complete_reading(request: Request):
    """Log completion of a reading/flashcard session."""
    student_id = get_student_id(request) or 1
    body = await request.json()
    item_ids = body.get("item_ids", [])
    duration_seconds = body.get("duration_seconds")
    cards_reviewed = body.get("cards_reviewed", 0)

    db = await get_db()
    try:
        from app.services.srs import update_srs_after_practice
        # Record encounters as practiced
        for item_id in item_ids:
            await record_encounter(db, student_id, item_id, practiced=True)
            # Light SRS update: treat as low-quality practice (0.6 score)
            await update_srs_after_practice(db, item_id, 0.6, student_id=student_id)

        # Log in practice_log
        await db.execute(
            """INSERT INTO practice_log
               (item_ids, prompt, formality, transcript, overall_score,
                student_id, duration_seconds, practice_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (json.dumps(item_ids), "Reading practice", "n/a",
             f"{cards_reviewed} cards reviewed", 0.6,
             student_id, duration_seconds, "reading")
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()

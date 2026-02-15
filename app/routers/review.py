import json

from fastapi import APIRouter, HTTPException, Request
from app.database import get_db
from app.auth import get_student_id

router = APIRouter()


@router.get("/queue")
async def review_queue(request: Request):
    """Get items due for review, ordered by most overdue first."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT i.id, i.korean, i.english, i.item_type, i.topik_level,
                      s.next_review, s.interval_days, s.repetitions,
                      m.overall_score, m.practice_count
               FROM items i
               JOIN srs_state s ON s.item_id = i.id AND s.student_id = ?
               LEFT JOIN mastery m ON m.item_id = i.id AND m.student_id = ?
               WHERE s.next_review <= datetime('now')
               ORDER BY s.next_review ASC
               LIMIT 100""",
            (student_id, student_id)
        )
        items = []
        for r in rows:
            items.append({
                "id": r[0], "korean": r[1], "english": r[2],
                "item_type": r[3], "topik_level": r[4],
                "next_review": r[5], "interval_days": r[6],
                "repetitions": r[7], "overall_score": r[8],
                "practice_count": r[9],
            })
        return {"queue": items, "total_due": len(items)}
    finally:
        await db.close()


@router.get("/history")
async def practice_history(request: Request, limit: int = 20):
    """Get recent practice sessions."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT id, item_ids, prompt, formality, transcript,
                      overall_score, created_at
               FROM practice_log
               WHERE student_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (student_id, limit)
        )
        sessions = []
        for r in rows:
            sessions.append({
                "id": r[0], "item_ids": r[1], "prompt": r[2],
                "formality": r[3], "transcript": r[4],
                "overall_score": r[5], "created_at": r[6],
            })
        return {"sessions": sessions}
    finally:
        await db.close()


@router.get("/history/{session_id}")
async def practice_session_detail(session_id: int, request: Request):
    """Get full detail for a single practice session including feedback."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT id, item_ids, prompt, formality, transcript,
                      overall_score, feedback_json, created_at
               FROM practice_log WHERE id = ? AND student_id = ?""",
            (session_id, student_id)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")
        row = rows[0]

        item_ids = json.loads(row[1]) if row[1] else []
        feedback = json.loads(row[6]) if row[6] else None

        # Fetch item names for display
        items = []
        if item_ids:
            placeholders = ",".join("?" for _ in item_ids)
            item_rows = await db.execute_fetchall(
                f"SELECT id, korean, english, item_type FROM items WHERE id IN ({placeholders})",
                item_ids
            )
            for ir in item_rows:
                items.append({
                    "id": ir[0], "korean": ir[1],
                    "english": ir[2], "item_type": ir[3],
                })

        return {
            "id": row[0], "item_ids": item_ids, "prompt": row[2],
            "formality": row[3], "transcript": row[4],
            "overall_score": row[5], "feedback": feedback,
            "created_at": row[7], "items": items,
        }
    finally:
        await db.close()

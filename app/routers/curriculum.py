"""Curriculum browser - HowToStudyKorean.com lesson structure."""

from fastapi import APIRouter, Request
from app.database import get_db
from app.auth import get_student_id

router = APIRouter()


@router.get("/units")
async def list_units(request: Request):
    """Get all curriculum units with lesson counts."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT u.id, u.unit_number, u.title, u.description, u.topik_level, u.url,
                      COUNT(l.id) as lesson_count
               FROM curriculum_units u
               LEFT JOIN curriculum_lessons l ON l.unit_id = u.id
               GROUP BY u.id
               ORDER BY u.unit_number"""
        )

        units = []
        for r in rows:
            units.append({
                "id": r[0],
                "unit_number": r[1],
                "title": r[2],
                "description": r[3],
                "topik_level": r[4],
                "url": r[5],
                "lesson_count": r[6]
            })

        return {"units": units}
    finally:
        await db.close()


@router.get("/units/{unit_id}/lessons")
async def list_lessons(unit_id: int, request: Request):
    """Get all lessons in a unit with progress info."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        # Get unit info
        unit_rows = await db.execute_fetchall(
            "SELECT unit_number, title FROM curriculum_units WHERE id = ?",
            (unit_id,)
        )
        if not unit_rows:
            return {"error": "Unit not found"}

        # Get lessons with progress
        rows = await db.execute_fetchall(
            """SELECT l.id, l.lesson_number, l.title, l.url, l.description,
                      lp.status, lp.mastery_score, lp.practice_count,
                      COUNT(DISTINCT li.item_id) as item_count
               FROM curriculum_lessons l
               LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.student_id = ?
               LEFT JOIN lesson_items li ON li.lesson_id = l.id
               WHERE l.unit_id = ?
               GROUP BY l.id
               ORDER BY l.sort_order""",
            (student_id, unit_id)
        )

        lessons = []
        for r in rows:
            lessons.append({
                "id": r[0],
                "lesson_number": r[1],
                "title": r[2],
                "url": r[3],
                "description": r[4],
                "status": r[5] or "available",
                "mastery_score": r[6] or 0.0,
                "practice_count": r[7] or 0,
                "item_count": r[8]
            })

        return {
            "unit": {
                "id": unit_id,
                "unit_number": unit_rows[0][0],
                "title": unit_rows[0][1]
            },
            "lessons": lessons
        }
    finally:
        await db.close()


@router.get("/lessons/{lesson_id}")
async def get_lesson_detail(lesson_id: int, request: Request):
    """Get detailed info about a specific lesson including items."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        # Get lesson info
        lesson_rows = await db.execute_fetchall(
            """SELECT l.id, l.lesson_number, l.title, l.url, l.description,
                      u.unit_number, u.title as unit_title,
                      lp.status, lp.mastery_score, lp.practice_count
               FROM curriculum_lessons l
               JOIN curriculum_units u ON u.id = l.unit_id
               LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.student_id = ?
               WHERE l.id = ?""",
            (student_id, lesson_id)
        )

        if not lesson_rows:
            return {"error": "Lesson not found"}

        r = lesson_rows[0]
        lesson = {
            "id": r[0],
            "lesson_number": r[1],
            "title": r[2],
            "url": r[3],
            "description": r[4],
            "unit_number": r[5],
            "unit_title": r[6],
            "status": r[7] or "available",
            "mastery_score": r[8] or 0.0,
            "practice_count": r[9] or 0
        }

        # Get items in this lesson
        item_rows = await db.execute_fetchall(
            """SELECT i.id, i.korean, i.english, i.item_type, i.topik_level,
                      m.overall_score, m.practice_count as item_practice_count
               FROM lesson_items li
               JOIN items i ON i.id = li.item_id
               LEFT JOIN mastery m ON m.item_id = i.id AND m.student_id = ?
               WHERE li.lesson_id = ?
               ORDER BY li.introduced_order""",
            (student_id, lesson_id)
        )

        items = []
        for ir in item_rows:
            items.append({
                "id": ir[0],
                "korean": ir[1],
                "english": ir[2],
                "item_type": ir[3],
                "topik_level": ir[4],
                "mastery_score": ir[5] or 0.0,
                "practice_count": ir[6] or 0
            })

        lesson["items"] = items

        return {"lesson": lesson}
    finally:
        await db.close()

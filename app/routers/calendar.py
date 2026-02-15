from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from app.database import get_db
from app.auth import require_teacher, get_student_id
from datetime import datetime, timedelta
import json

router = APIRouter()


@router.get("/assignments", dependencies=[Depends(require_teacher)])
async def get_assignments(student_id: int = None, start_date: str = None, end_date: str = None):
    """Get curriculum assignments. Filter by student and/or date range."""
    db = await get_db()
    try:
        query = """
            SELECT a.id, a.student_id, s.display_name as student_name,
                   a.assignment_type, a.lesson_id, a.sentence_id, a.item_id,
                   a.assigned_date, a.due_date, a.completed_at, a.notes,
                   l.lesson_number, l.title as lesson_title,
                   sen.korean as sentence_korean,
                   i.korean as item_korean, i.english as item_english
            FROM curriculum_assignments a
            JOIN students s ON s.id = a.student_id
            LEFT JOIN curriculum_lessons l ON l.id = a.lesson_id
            LEFT JOIN sentences sen ON sen.id = a.sentence_id
            LEFT JOIN items i ON i.id = a.item_id
            WHERE 1=1
        """
        params = []

        if student_id:
            query += " AND a.student_id = ?"
            params.append(student_id)
        if start_date:
            query += " AND a.due_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND a.due_date <= ?"
            params.append(end_date)

        query += " ORDER BY a.due_date ASC, a.assigned_date ASC"

        rows = await db.execute_fetchall(query, params)

        assignments = []
        for r in rows:
            assignment = {
                "id": r[0],
                "student_id": r[1],
                "student_name": r[2],
                "assignment_type": r[3],
                "lesson_id": r[4],
                "sentence_id": r[5],
                "item_id": r[6],
                "assigned_date": r[7],
                "due_date": r[8],
                "completed_at": r[9],
                "notes": r[10],
                "lesson_number": r[11],
                "lesson_title": r[12],
                "sentence_korean": r[13],
                "item_korean": r[14],
                "item_english": r[15],
            }
            assignments.append(assignment)

        return {"assignments": assignments}
    finally:
        await db.close()


@router.post("/assignments", dependencies=[Depends(require_teacher)])
async def create_assignment(request: Request):
    """Create a new curriculum assignment."""
    body = await request.json()
    student_id = body.get("student_id")
    assignment_type = body.get("assignment_type")  # 'lesson', 'sentence', 'vocab'
    lesson_id = body.get("lesson_id")
    sentence_id = body.get("sentence_id")
    item_id = body.get("item_id")
    due_date = body.get("due_date")  # ISO date string
    notes = body.get("notes", "")

    if not student_id or not assignment_type or not due_date:
        return JSONResponse({"error": "Missing required fields"}, status_code=400)

    # Validate assignment type has corresponding ID
    if assignment_type == "lesson" and not lesson_id:
        return JSONResponse({"error": "lesson_id required for lesson assignment"}, status_code=400)
    elif assignment_type == "sentence" and not sentence_id:
        return JSONResponse({"error": "sentence_id required for sentence assignment"}, status_code=400)
    elif assignment_type == "vocab" and not item_id:
        return JSONResponse({"error": "item_id required for vocab assignment"}, status_code=400)

    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO curriculum_assignments
               (student_id, assignment_type, lesson_id, sentence_id, item_id, due_date, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (student_id, assignment_type, lesson_id, sentence_id, item_id, due_date, notes)
        )
        await db.commit()
        return {"id": cursor.lastrowid, "success": True}
    finally:
        await db.close()


@router.put("/assignments/{assignment_id}", dependencies=[Depends(require_teacher)])
async def update_assignment(assignment_id: int, request: Request):
    """Update an assignment (change due date, notes, mark complete, etc.)."""
    body = await request.json()
    due_date = body.get("due_date")
    notes = body.get("notes")
    completed_at = body.get("completed_at")  # ISO datetime string or null

    updates = []
    params = []

    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if completed_at is not None:
        updates.append("completed_at = ?")
        params.append(completed_at if completed_at else None)

    if not updates:
        return JSONResponse({"error": "No fields to update"}, status_code=400)

    params.append(assignment_id)

    db = await get_db()
    try:
        await db.execute(
            f"UPDATE curriculum_assignments SET {', '.join(updates)} WHERE id = ?",
            params
        )
        await db.commit()
        return {"success": True}
    finally:
        await db.close()


@router.delete("/assignments/{assignment_id}", dependencies=[Depends(require_teacher)])
async def delete_assignment(assignment_id: int):
    """Delete an assignment."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM curriculum_assignments WHERE id = ?", (assignment_id,))
        await db.commit()
        return {"success": True}
    finally:
        await db.close()


@router.get("/student/{student_id}/upcoming")
async def get_student_upcoming(request: Request, student_id: int):
    """Get upcoming assignments for a student (for student view)."""
    # Verify the requesting user is the student or a teacher
    requesting_student_id = get_student_id(request)
    if requesting_student_id != student_id:
        # Check if teacher
        try:
            from app.auth import require_teacher
            await require_teacher(request)
        except:
            return JSONResponse({"error": "Unauthorized"}, status_code=403)

    db = await get_db()
    try:
        today = datetime.now().date().isoformat()
        week_from_now = (datetime.now() + timedelta(days=7)).date().isoformat()

        rows = await db.execute_fetchall(
            """SELECT a.id, a.assignment_type, a.due_date, a.completed_at, a.notes,
                      l.lesson_number, l.title as lesson_title,
                      sen.korean as sentence_korean, sen.english as sentence_english,
                      i.korean as item_korean, i.english as item_english
               FROM curriculum_assignments a
               LEFT JOIN curriculum_lessons l ON l.id = a.lesson_id
               LEFT JOIN sentences sen ON sen.id = a.sentence_id
               LEFT JOIN items i ON i.id = a.item_id
               WHERE a.student_id = ? AND a.due_date >= ? AND a.due_date <= ? AND a.completed_at IS NULL
               ORDER BY a.due_date ASC""",
            (student_id, today, week_from_now)
        )

        assignments = []
        for r in rows:
            assignment = {
                "id": r[0],
                "assignment_type": r[1],
                "due_date": r[2],
                "completed_at": r[3],
                "notes": r[4],
                "lesson_number": r[5],
                "lesson_title": r[6],
                "sentence_korean": r[7],
                "sentence_english": r[8],
                "item_korean": r[9],
                "item_english": r[10],
            }
            assignments.append(assignment)

        return {"assignments": assignments}
    finally:
        await db.close()


@router.post("/assignments/{assignment_id}/complete")
async def complete_assignment(request: Request, assignment_id: int):
    """Mark an assignment as complete (called after practice)."""
    student_id = get_student_id(request) or 1

    db = await get_db()
    try:
        # Verify assignment belongs to this student
        rows = await db.execute_fetchall(
            "SELECT student_id FROM curriculum_assignments WHERE id = ?",
            (assignment_id,)
        )
        if not rows or rows[0][0] != student_id:
            return JSONResponse({"error": "Assignment not found"}, status_code=404)

        await db.execute(
            "UPDATE curriculum_assignments SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (assignment_id,)
        )
        await db.commit()
        return {"success": True}
    finally:
        await db.close()

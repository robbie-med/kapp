"""Student goal tracking endpoints."""

from fastapi import APIRouter, Request
from app.database import get_db
from app.models import GoalCreate
from app.auth import get_student_id

router = APIRouter()


@router.get("")
async def list_goals(request: Request, active_only: bool = True):
    """List goals for the current student with dynamically calculated progress."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        condition = "AND g.active = 1" if active_only else ""
        rows = await db.execute_fetchall(
            f"""SELECT g.id, g.goal_type, g.target_value, g.current_value,
                       g.period, g.deadline, g.created_at, g.completed_at, g.active
                FROM goals g
                WHERE g.student_id = ? {condition}
                ORDER BY g.active DESC, g.created_at DESC""",
            (student_id,)
        )
        goals = []
        for r in rows:
            target = r[2]
            current = await _calculate_goal_progress(db, student_id, r[1], r[2],
                                                       r[4], r[5], r[6])
            pct = min(current / target * 100, 100) if target > 0 else 0
            goals.append({
                "id": r[0], "goal_type": r[1], "target_value": target,
                "current_value": current, "period": r[4],
                "deadline": r[5], "created_at": r[6],
                "completed_at": r[7], "active": bool(r[8]),
                "progress_pct": round(pct, 1),
            })
        return {"goals": goals}
    finally:
        await db.close()


async def _calculate_goal_progress(db, student_id, goal_type, target,
                                     period, deadline, created_at):
    """Calculate current progress for a goal dynamically from practice_log."""
    # Determine the time window
    if period == "daily":
        time_filter = "AND created_at >= datetime('now', 'start of day')"
    elif period == "weekly":
        time_filter = "AND created_at >= datetime('now', '-7 days')"
    elif deadline:
        time_filter = f"AND created_at >= '{created_at}' AND created_at <= '{deadline}'"
    else:
        time_filter = f"AND created_at >= '{created_at}'"

    if goal_type == "practice_sessions":
        rows = await db.execute_fetchall(
            f"SELECT COUNT(*) FROM practice_log WHERE student_id = ? {time_filter}",
            (student_id,)
        )
        return rows[0][0]
    elif goal_type == "new_items":
        rows = await db.execute_fetchall(
            f"""SELECT COUNT(*) FROM encounters
                WHERE student_id = ? AND first_practiced IS NOT NULL {time_filter.replace('created_at', 'first_practiced')}""",
            (student_id,)
        )
        return rows[0][0]
    elif goal_type == "study_time":
        rows = await db.execute_fetchall(
            f"""SELECT COALESCE(SUM(duration_seconds), 0) / 60 FROM practice_log
                WHERE student_id = ? {time_filter}""",
            (student_id,)
        )
        return int(rows[0][0])
    return 0


@router.post("")
async def create_goal(req: GoalCreate, request: Request):
    """Create a new goal for the current student."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO goals (student_id, goal_type, target_value, period, deadline)
               VALUES (?, ?, ?, ?, ?)""",
            (student_id, req.goal_type, req.target_value, req.period, req.deadline)
        )
        await db.commit()
        return {"id": cursor.lastrowid}
    finally:
        await db.close()


@router.delete("/{goal_id}")
async def delete_goal(goal_id: int, request: Request):
    """Deactivate a goal (soft delete)."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        await db.execute(
            "UPDATE goals SET active = 0 WHERE id = ? AND student_id = ?",
            (goal_id, student_id)
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()

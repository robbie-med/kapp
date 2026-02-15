from fastapi import APIRouter, Request, Depends
from app.database import get_db, calculate_student_level
from app.auth import get_student_id, require_teacher

router = APIRouter()


@router.get("")
async def get_stats(request: Request):
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        # Overall counts (items are shared)
        total = await db.execute_fetchall("SELECT COUNT(*) FROM items")
        vocab_count = await db.execute_fetchall("SELECT COUNT(*) FROM items WHERE item_type='vocab'")
        grammar_count = await db.execute_fetchall("SELECT COUNT(*) FROM items WHERE item_type='grammar'")

        # Items by TOPIK level
        by_level = await db.execute_fetchall(
            "SELECT topik_level, COUNT(*) FROM items GROUP BY topik_level ORDER BY topik_level"
        )

        # Due for review (per student)
        due = await db.execute_fetchall(
            "SELECT COUNT(*) FROM srs_state WHERE student_id = ? AND next_review <= datetime('now')",
            (student_id,)
        )

        # Mastery distribution (per student)
        mastery_dist = await db.execute_fetchall(
            """SELECT
                SUM(CASE WHEN overall_score >= 0.8 THEN 1 ELSE 0 END) as mastered,
                SUM(CASE WHEN overall_score >= 0.5 AND overall_score < 0.8 THEN 1 ELSE 0 END) as learning,
                SUM(CASE WHEN overall_score < 0.5 AND practice_count > 0 THEN 1 ELSE 0 END) as struggling,
                SUM(CASE WHEN practice_count = 0 THEN 1 ELSE 0 END) as unseen
               FROM mastery WHERE student_id = ?""",
            (student_id,)
        )

        # Recent practice count (last 7 days, per student)
        recent = await db.execute_fetchall(
            "SELECT COUNT(*) FROM practice_log WHERE student_id = ? AND created_at >= datetime('now', '-7 days')",
            (student_id,)
        )

        # Average score (last 7 days, per student)
        avg_score = await db.execute_fetchall(
            "SELECT AVG(overall_score) FROM practice_log WHERE student_id = ? AND created_at >= datetime('now', '-7 days') AND overall_score IS NOT NULL",
            (student_id,)
        )

        # Student level
        level_rows = await db.execute_fetchall(
            """SELECT estimated_level FROM student_level_history
               WHERE student_id = ? ORDER BY calculated_at DESC LIMIT 1""",
            (student_id,)
        )
        current_level = level_rows[0][0] if level_rows else None

        # Encounter count
        encounter_count = await db.execute_fetchall(
            "SELECT COUNT(*) FROM encounters WHERE student_id = ?",
            (student_id,)
        )

        # Study time tracking
        total_study_time = await db.execute_fetchall(
            "SELECT COALESCE(SUM(duration_seconds), 0) FROM practice_log WHERE student_id = ?",
            (student_id,)
        )
        study_time_7d = await db.execute_fetchall(
            "SELECT COALESCE(SUM(duration_seconds), 0) FROM practice_log WHERE student_id = ? AND created_at >= datetime('now', '-7 days')",
            (student_id,)
        )

        md = mastery_dist[0] if mastery_dist else (0, 0, 0, 0)
        return {
            "total_items": total[0][0],
            "vocab_count": vocab_count[0][0],
            "grammar_count": grammar_count[0][0],
            "by_level": [{"level": r[0], "count": r[1]} for r in by_level],
            "due_for_review": due[0][0],
            "mastery": {
                "mastered": md[0] or 0,
                "learning": md[1] or 0,
                "struggling": md[2] or 0,
                "unseen": md[3] or 0,
            },
            "recent_practice_count": recent[0][0],
            "recent_avg_score": round(avg_score[0][0], 2) if avg_score[0][0] else None,
            "estimated_level": current_level,
            "items_encountered": encounter_count[0][0],
            "total_study_seconds": total_study_time[0][0],
            "study_seconds_7d": study_time_7d[0][0],
        }
    finally:
        await db.close()


@router.get("/level-history")
async def get_level_history(request: Request):
    """Get student's TOPIK level progression over time."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT estimated_level, calculated_at FROM student_level_history
               WHERE student_id = ? ORDER BY calculated_at ASC""",
            (student_id,)
        )
        return {
            "history": [{"level": r[0], "date": r[1]} for r in rows]
        }
    finally:
        await db.close()


@router.get("/encounters")
async def get_encounters(request: Request):
    """Get student's encounter data — items they've seen/practiced."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT e.item_id, i.korean, i.english, i.item_type, i.topik_level,
                      e.first_seen, e.first_practiced, e.encounter_count
               FROM encounters e
               JOIN items i ON i.id = e.item_id
               WHERE e.student_id = ?
               ORDER BY e.first_seen DESC
               LIMIT 100""",
            (student_id,)
        )
        return {
            "total": len(rows),
            "encounters": [{
                "item_id": r[0], "korean": r[1], "english": r[2],
                "item_type": r[3], "topik_level": r[4],
                "first_seen": r[5], "first_practiced": r[6],
                "encounter_count": r[7],
            } for r in rows]
        }
    finally:
        await db.close()


@router.get("/activity")
async def get_activity(request: Request, days: int = 30):
    """Practice activity over the last N days — daily practice count and avg score."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT DATE(created_at) as day,
                      COUNT(*) as session_count,
                      AVG(overall_score) as avg_score,
                      COALESCE(SUM(duration_seconds), 0) as study_seconds
               FROM practice_log
               WHERE student_id = ? AND created_at >= datetime('now', ?)
               GROUP BY DATE(created_at)
               ORDER BY day ASC""",
            (student_id, f'-{days} days')
        )
        return {
            "activity": [{
                "date": r[0],
                "sessions": r[1],
                "avg_score": round(r[2], 2) if r[2] else None,
                "study_seconds": r[3],
            } for r in rows]
        }
    finally:
        await db.close()


@router.get("/mastery-by-level")
async def get_mastery_by_level(request: Request):
    """Mastery breakdown per TOPIK level for the current student."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT i.topik_level,
                      COUNT(*) as total,
                      SUM(CASE WHEN m.overall_score >= 0.8 THEN 1 ELSE 0 END) as mastered,
                      SUM(CASE WHEN m.overall_score >= 0.5 AND m.overall_score < 0.8 THEN 1 ELSE 0 END) as learning,
                      SUM(CASE WHEN m.overall_score < 0.5 AND m.practice_count > 0 THEN 1 ELSE 0 END) as struggling,
                      SUM(CASE WHEN m.practice_count = 0 THEN 1 ELSE 0 END) as unseen,
                      AVG(CASE WHEN m.practice_count > 0 THEN m.overall_score END) as avg_score
               FROM mastery m
               JOIN items i ON i.id = m.item_id
               WHERE m.student_id = ?
               GROUP BY i.topik_level
               ORDER BY i.topik_level""",
            (student_id,)
        )
        return {
            "levels": [{
                "level": r[0], "total": r[1],
                "mastered": r[2] or 0, "learning": r[3] or 0,
                "struggling": r[4] or 0, "unseen": r[5] or 0,
                "avg_score": round(r[6], 2) if r[6] else None,
            } for r in rows]
        }
    finally:
        await db.close()


@router.get("/vocab-growth")
async def get_vocab_growth(request: Request, days: int = 90):
    """Cumulative items encountered over time."""
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT DATE(first_seen) as day, COUNT(*) as new_items
               FROM encounters
               WHERE student_id = ? AND first_seen >= datetime('now', ?)
               GROUP BY DATE(first_seen)
               ORDER BY day ASC""",
            (student_id, f'-{days} days')
        )
        # Make cumulative
        cumulative = []
        total = 0
        for r in rows:
            total += r[1]
            cumulative.append({"date": r[0], "new": r[1], "cumulative": total})
        return {"growth": cumulative}
    finally:
        await db.close()


@router.get("/teacher/overview", dependencies=[Depends(require_teacher)])
async def teacher_overview():
    """Teacher dashboard: overview of all students' progress."""
    db = await get_db()
    try:
        students = await db.execute_fetchall(
            "SELECT id, username, display_name, created_at FROM students ORDER BY id"
        )
        total_items = await db.execute_fetchall("SELECT COUNT(*) FROM items")

        result = []
        for s in students:
            sid = s[0]

            # Practice count (all time + last 7 days)
            total_practices = await db.execute_fetchall(
                "SELECT COUNT(*) FROM practice_log WHERE student_id = ?", (sid,)
            )
            recent_practices = await db.execute_fetchall(
                "SELECT COUNT(*) FROM practice_log WHERE student_id = ? AND created_at >= datetime('now', '-7 days')",
                (sid,)
            )
            # Average score (last 7 days)
            avg_score = await db.execute_fetchall(
                "SELECT AVG(overall_score) FROM practice_log WHERE student_id = ? AND created_at >= datetime('now', '-7 days') AND overall_score IS NOT NULL",
                (sid,)
            )
            # Last practice date
            last_practice = await db.execute_fetchall(
                "SELECT MAX(created_at) FROM practice_log WHERE student_id = ?", (sid,)
            )
            # Due for review
            due = await db.execute_fetchall(
                "SELECT COUNT(*) FROM srs_state WHERE student_id = ? AND next_review <= datetime('now')",
                (sid,)
            )
            # Mastery distribution
            mastery = await db.execute_fetchall(
                """SELECT
                    SUM(CASE WHEN overall_score >= 0.8 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN overall_score >= 0.5 AND overall_score < 0.8 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN overall_score < 0.5 AND practice_count > 0 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN practice_count = 0 THEN 1 ELSE 0 END)
                   FROM mastery WHERE student_id = ?""",
                (sid,)
            )
            # Estimated level
            level_row = await db.execute_fetchall(
                "SELECT estimated_level FROM student_level_history WHERE student_id = ? ORDER BY calculated_at DESC LIMIT 1",
                (sid,)
            )
            # Items encountered
            enc_count = await db.execute_fetchall(
                "SELECT COUNT(*) FROM encounters WHERE student_id = ?", (sid,)
            )

            md = mastery[0] if mastery and mastery[0][0] is not None else (0, 0, 0, 0)
            result.append({
                "id": sid,
                "username": s[1],
                "display_name": s[2],
                "created_at": s[3],
                "total_practices": total_practices[0][0],
                "recent_practices": recent_practices[0][0],
                "recent_avg_score": round(avg_score[0][0], 2) if avg_score[0][0] else None,
                "last_practice": last_practice[0][0],
                "due_for_review": due[0][0],
                "mastery": {
                    "mastered": md[0] or 0,
                    "learning": md[1] or 0,
                    "struggling": md[2] or 0,
                    "unseen": md[3] or 0,
                },
                "estimated_level": level_row[0][0] if level_row else None,
                "items_encountered": enc_count[0][0],
            })

        return {
            "total_items": total_items[0][0],
            "students": result,
        }
    finally:
        await db.close()


@router.get("/weaknesses")
async def get_weaknesses(request: Request, limit: int = 20):
    """
    Identify items with poor absorption or high error rates.
    Returns items sorted by weakness score (combination of low absorption, high errors, stagnation).
    """
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        # Query items with comprehensive metrics
        rows = await db.execute_fetchall(
            """SELECT i.id, i.korean, i.english, i.item_type, i.topik_level,
                      m.exposure_count, m.usage_count, m.error_count,
                      m.overall_score, m.practice_count, m.last_practiced
               FROM items i
               JOIN mastery m ON m.item_id = i.id
               WHERE m.student_id = ? AND m.exposure_count > 0
               ORDER BY
                   -- Weakness score: high exposure + low usage + high errors + low mastery
                   CASE
                       WHEN m.usage_count = 0 THEN m.exposure_count * 2.0
                       ELSE (m.error_count::REAL / NULLIF(m.usage_count, 0)) * m.exposure_count * (1.0 - m.overall_score)
                   END DESC
               LIMIT ?""",
            (student_id, limit)
        )

        result = []
        for r in rows:
            absorption_rate = (r[6] / r[5]) if r[5] > 0 else 0.0  # usage / exposure
            error_rate = (r[7] / r[6]) if r[6] > 0 else 0.0  # errors / usage
            is_stagnant = r[5] >= 5 and r[8] < 0.5  # exposure >= 5 and mastery < 0.5

            result.append({
                "id": r[0],
                "korean": r[1],
                "english": r[2],
                "item_type": r[3],
                "topik_level": r[4],
                "exposure_count": r[5],
                "usage_count": r[6],
                "error_count": r[7],
                "overall_score": r[8],
                "absorption_rate": round(absorption_rate, 2),
                "error_rate": round(error_rate, 2),
                "is_stagnant": is_stagnant,
                "last_practiced": r[10],
                "weakness_type": "not_absorbing" if absorption_rate < 0.3 and r[5] > 3 else (
                    "high_errors" if error_rate > 0.5 and r[6] > 2 else (
                        "stagnant" if is_stagnant else "needs_practice"
                    )
                )
            })

        return {"weaknesses": result}
    finally:
        await db.close()


@router.get("/item-timeline/{item_id}")
async def get_item_timeline(item_id: int, request: Request, days: int = 30):
    """
    Get temporal data for a specific item: when it was exposed, used correctly, used incorrectly.
    """
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        # Get item details
        item_row = await db.execute_fetchall(
            "SELECT korean, english, item_type FROM items WHERE id = ?",
            (item_id,)
        )
        if not item_row:
            return {"error": "Item not found"}

        # Get encounter timeline
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        encounters = await db.execute_fetchall(
            """SELECT DATE(first_seen) as date, encounter_type, COUNT(*) as count
               FROM encounters
               WHERE student_id = ? AND item_id = ? AND first_seen >= ?
               GROUP BY date, encounter_type
               ORDER BY date ASC""",
            (student_id, item_id, cutoff)
        )

        # Get current metrics
        metrics = await db.execute_fetchall(
            """SELECT exposure_count, usage_count, error_count, overall_score
               FROM mastery WHERE student_id = ? AND item_id = ?""",
            (student_id, item_id)
        )

        timeline = []
        for e in encounters:
            timeline.append({
                "date": e[0],
                "type": e[1],
                "count": e[2]
            })

        return {
            "item": {
                "id": item_id,
                "korean": item_row[0][0],
                "english": item_row[0][1],
                "item_type": item_row[0][2]
            },
            "metrics": {
                "exposure_count": metrics[0][0] if metrics else 0,
                "usage_count": metrics[0][1] if metrics else 0,
                "error_count": metrics[0][2] if metrics else 0,
                "overall_score": metrics[0][3] if metrics else 0.0
            },
            "timeline": timeline
        }
    finally:
        await db.close()


@router.get("/error-patterns")
async def get_error_patterns(request: Request, limit: int = 20):
    """
    Identify common error patterns: which items are frequently used incorrectly.
    Groups by item_type and grammar_category for pattern analysis.
    """
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        # Top items with highest error rates
        top_errors = await db.execute_fetchall(
            """SELECT i.id, i.korean, i.english, i.item_type, i.grammar_category,
                      m.error_count, m.usage_count,
                      ROUND(m.error_count::REAL / NULLIF(m.usage_count, 0), 2) as error_rate
               FROM items i
               JOIN mastery m ON m.item_id = i.id
               WHERE m.student_id = ? AND m.usage_count > 0 AND m.error_count > 0
               ORDER BY error_rate DESC, m.error_count DESC
               LIMIT ?""",
            (student_id, limit)
        )

        # Group by item type
        type_patterns = await db.execute_fetchall(
            """SELECT i.item_type,
                      COUNT(*) as item_count,
                      SUM(m.error_count) as total_errors,
                      SUM(m.usage_count) as total_usage,
                      ROUND(SUM(m.error_count)::REAL / NULLIF(SUM(m.usage_count), 0), 2) as avg_error_rate
               FROM items i
               JOIN mastery m ON m.item_id = i.id
               WHERE m.student_id = ? AND m.usage_count > 0
               GROUP BY i.item_type""",
            (student_id,)
        )

        # Group by grammar category (for grammar items)
        grammar_patterns = await db.execute_fetchall(
            """SELECT i.grammar_category,
                      COUNT(*) as item_count,
                      SUM(m.error_count) as total_errors,
                      SUM(m.usage_count) as total_usage,
                      ROUND(SUM(m.error_count)::REAL / NULLIF(SUM(m.usage_count), 0), 2) as avg_error_rate
               FROM items i
               JOIN mastery m ON m.item_id = i.id
               WHERE m.student_id = ? AND i.item_type = 'grammar' AND m.usage_count > 0
                     AND i.grammar_category IS NOT NULL
               GROUP BY i.grammar_category
               ORDER BY avg_error_rate DESC""",
            (student_id,)
        )

        return {
            "top_errors": [{
                "id": r[0], "korean": r[1], "english": r[2], "item_type": r[3],
                "grammar_category": r[4], "error_count": r[5], "usage_count": r[6],
                "error_rate": r[7]
            } for r in top_errors],
            "by_type": [{
                "item_type": r[0], "item_count": r[1], "total_errors": r[2],
                "total_usage": r[3], "avg_error_rate": r[4]
            } for r in type_patterns],
            "by_grammar_category": [{
                "category": r[0], "item_count": r[1], "total_errors": r[2],
                "total_usage": r[3], "avg_error_rate": r[4]
            } for r in grammar_patterns]
        }
    finally:
        await db.close()

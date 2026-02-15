"""SM-2 spaced repetition with weakness weighting."""

import math
from datetime import datetime, timedelta
import aiosqlite
from app.database import ensure_student_item_state


async def select_review_items(db: aiosqlite.Connection, count: int = 3,
                               topik_level: int | None = None,
                               student_id: int = 1,
                               new_items_per_session: int = 2) -> list[dict]:
    """Select items for practice with 4-tier priority:
    0. Teacher-assigned unseen items (source: telegram/signal/manual)
    1. Overdue items (teacher-assigned boosted to front)
    2. Lowest mastery items
    3. Curriculum-ordered unseen items (topik_level ASC, id ASC)
    """
    level_filter = "AND i.topik_level = ?" if topik_level else ""
    level_params = [topik_level] if topik_level else []
    items = []

    # Tier 0: Teacher-assigned unseen items (always prioritized)
    teacher_unseen = await db.execute_fetchall(
        f"""SELECT i.id, i.korean, i.english, i.item_type, i.topik_level,
                   NULL as overall_score, datetime('now') as next_review
            FROM items i
            WHERE i.source IN ('telegram', 'signal', 'manual')
                  AND i.id NOT IN (SELECT item_id FROM srs_state WHERE student_id = ?)
                  {level_filter}
            ORDER BY i.created_at ASC
            LIMIT ?""",
        [student_id] + level_params + [count]
    )
    for r in teacher_unseen:
        item = _row_to_dict(r)
        await ensure_student_item_state(db, item["id"], student_id)
        items.append(item)

    # Tier 1: Overdue items (teacher-assigned first)
    if len(items) < count:
        existing_ids = [i["id"] for i in items]
        placeholders = ",".join("?" * len(existing_ids)) if existing_ids else "0"
        remaining = count - len(items)

        overdue = await db.execute_fetchall(
            f"""SELECT i.id, i.korean, i.english, i.item_type, i.topik_level,
                       m.overall_score, s.next_review
                FROM items i
                JOIN srs_state s ON s.item_id = i.id AND s.student_id = ?
                LEFT JOIN mastery m ON m.item_id = i.id AND m.student_id = ?
                WHERE s.next_review <= datetime('now')
                      AND i.id NOT IN ({placeholders}) {level_filter}
                ORDER BY
                    CASE WHEN i.source IN ('telegram','signal','manual') THEN 0 ELSE 1 END,
                    s.next_review ASC
                LIMIT ?""",
            [student_id, student_id] + existing_ids + level_params + [remaining]
        )
        items.extend([_row_to_dict(r) for r in overdue])

    # Tier 2: Lowest mastery items
    if len(items) < count:
        existing_ids = [i["id"] for i in items]
        placeholders = ",".join("?" * len(existing_ids)) if existing_ids else "0"
        remaining = count - len(items)

        weak = await db.execute_fetchall(
            f"""SELECT i.id, i.korean, i.english, i.item_type, i.topik_level,
                       m.overall_score, s.next_review
                FROM items i
                JOIN srs_state s ON s.item_id = i.id AND s.student_id = ?
                LEFT JOIN mastery m ON m.item_id = i.id AND m.student_id = ?
                WHERE i.id NOT IN ({placeholders}) {level_filter}
                ORDER BY COALESCE(m.overall_score, 0) ASC, RANDOM()
                LIMIT ?""",
            [student_id, student_id] + existing_ids + level_params + [remaining]
        )
        items.extend([_row_to_dict(r) for r in weak])

    # Tier 3: Curriculum-ordered unseen items (capped by new_items_per_session)
    if len(items) < count:
        existing_ids = [i["id"] for i in items]
        placeholders = ",".join("?" * len(existing_ids)) if existing_ids else "0"
        remaining = count - len(items)
        new_item_limit = min(remaining, new_items_per_session)

        unseen = await db.execute_fetchall(
            f"""SELECT i.id, i.korean, i.english, i.item_type, i.topik_level,
                       NULL as overall_score, datetime('now') as next_review
                FROM items i
                WHERE i.id NOT IN (SELECT item_id FROM srs_state WHERE student_id = ?)
                      AND i.id NOT IN ({placeholders}) {level_filter}
                ORDER BY i.topik_level ASC, i.id ASC
                LIMIT ?""",
            [student_id] + existing_ids + level_params + [new_item_limit]
        )
        for r in unseen:
            item = _row_to_dict(r)
            await ensure_student_item_state(db, item["id"], student_id)
            items.append(item)

        # Update curriculum state
        if unseen:
            from app.database import get_curriculum_state, upsert_curriculum_state
            state = await get_curriculum_state(db, student_id)
            if state:
                items_added = len(unseen)
                new_total = state["items_introduced"] + items_added
                max_level = max(r[4] for r in unseen)
                await upsert_curriculum_state(db, student_id, max_level, 0, new_total)
            else:
                # Initialize curriculum state
                items_added = len(unseen)
                max_level = max(r[4] for r in unseen)
                await upsert_curriculum_state(db, student_id, max_level, 0, items_added)

    return items


def _row_to_dict(r) -> dict:
    return {
        "id": r[0], "korean": r[1], "english": r[2],
        "item_type": r[3], "topik_level": r[4],
        "overall_score": r[5], "next_review": r[6],
    }


def calculate_sm2(quality: float, ease_factor: float, interval: float,
                   repetitions: int, sub_scores: dict | None = None) -> dict:
    """
    Modified SM-2 algorithm.
    quality: 0.0-1.0 (mapped to SM-2's 0-5 scale internally)
    sub_scores: optional dict with grammar_score, vocab_score, formality_score
    """
    q = quality * 5  # Map to 0-5

    if q < 3:
        # Failed: reset
        repetitions = 0
        interval = 0
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = interval * ease_factor

        repetitions += 1

    # Update ease factor
    ease_factor = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ease_factor = max(1.3, ease_factor)

    # Weakness multiplier
    if sub_scores:
        for key in ("grammar_score", "vocab_score", "formality_score"):
            score = sub_scores.get(key, 1.0)
            if score < 0.5:
                interval *= 0.5
            elif score < 0.75:
                interval *= 0.75

    interval = max(0, interval)
    next_review = datetime.utcnow() + timedelta(days=interval)

    return {
        "ease_factor": round(ease_factor, 2),
        "interval_days": round(interval, 1),
        "repetitions": repetitions,
        "next_review": next_review.isoformat(),
    }


async def update_srs_after_practice(db: aiosqlite.Connection, item_id: int,
                                     overall_score: float,
                                     sub_scores: dict | None = None,
                                     student_id: int = 1):
    """Update SRS state and mastery after a practice attempt."""
    await ensure_student_item_state(db, item_id, student_id)

    rows = await db.execute_fetchall(
        "SELECT ease_factor, interval_days, repetitions FROM srs_state WHERE item_id = ? AND student_id = ?",
        (item_id, student_id)
    )
    if not rows:
        return

    current = rows[0]
    new_state = calculate_sm2(
        overall_score, current[0], current[1], current[2], sub_scores
    )

    await db.execute(
        """UPDATE srs_state
           SET ease_factor = ?, interval_days = ?, repetitions = ?,
               next_review = ?, last_reviewed = datetime('now')
           WHERE item_id = ? AND student_id = ?""",
        (new_state["ease_factor"], new_state["interval_days"],
         new_state["repetitions"], new_state["next_review"], item_id, student_id)
    )

    # Update mastery
    if sub_scores:
        await db.execute(
            """UPDATE mastery SET
                grammar_score = (grammar_score * practice_count + ?) / (practice_count + 1),
                vocab_score = (vocab_score * practice_count + ?) / (practice_count + 1),
                formality_score = (formality_score * practice_count + ?) / (practice_count + 1),
                overall_score = (overall_score * practice_count + ?) / (practice_count + 1),
                practice_count = practice_count + 1,
                last_practiced = datetime('now'),
                updated_at = datetime('now')
            WHERE item_id = ? AND student_id = ?""",
            (sub_scores.get("grammar_score", overall_score),
             sub_scores.get("vocab_score", overall_score),
             sub_scores.get("formality_score", overall_score),
             overall_score, item_id, student_id)
        )
    else:
        await db.execute(
            """UPDATE mastery SET
                overall_score = (overall_score * practice_count + ?) / (practice_count + 1),
                practice_count = practice_count + 1,
                last_practiced = datetime('now'),
                updated_at = datetime('now')
            WHERE item_id = ? AND student_id = ?""",
            (overall_score, item_id, student_id)
        )

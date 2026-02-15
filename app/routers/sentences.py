"""Sentence management — teacher creates sentences, system links to items via dictionary form matching."""

import json
import re
from fastapi import APIRouter, Query, Depends, Request
from fastapi.responses import JSONResponse
from app.database import get_db, insert_sentence, find_matching_items
from app.models import SentenceCreate
from app.auth import require_teacher, get_student_id
from app.services.openai_service import chat_completion

router = APIRouter()


def _estimate_sentence_level(linked_items: list[dict]) -> int:
    """Estimate TOPIK level from linked items. Uses max level of linked items."""
    if not linked_items:
        return 1
    return max(item["topik_level"] for item in linked_items)


@router.get("")
async def list_sentences(
    search: str = Query(None),
    topik_level: int = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    db = await get_db()
    try:
        conditions = []
        params = []
        if search:
            conditions.append("(s.korean LIKE ? OR s.english LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if topik_level:
            conditions.append("s.topik_level = ?")
            params.append(topik_level)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * per_page

        count_row = await db.execute_fetchall(
            f"SELECT COUNT(*) FROM sentences s {where}", params
        )
        total = count_row[0][0]

        rows = await db.execute_fetchall(
            f"""SELECT s.id, s.korean, s.english, s.formality, s.topik_level, s.source, s.notes, s.created_at,
                       (SELECT COUNT(*) FROM sentence_items si WHERE si.sentence_id = s.id) as link_count
                FROM sentences s {where}
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset]
        )
        sentences = []
        for r in rows:
            sentences.append({
                "id": r[0], "korean": r[1], "english": r[2],
                "formality": r[3], "topik_level": r[4], "source": r[5],
                "notes": r[6], "created_at": r[7], "linked_item_count": r[8],
            })
        return {"sentences": sentences, "total": total, "page": page, "per_page": per_page}
    finally:
        await db.close()


@router.get("/{sentence_id}")
async def get_sentence(sentence_id: int):
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, korean, english, formality, topik_level, source, notes, created_at FROM sentences WHERE id = ?",
            (sentence_id,)
        )
        if not rows:
            return JSONResponse({"error": "Not found"}, status_code=404)
        r = rows[0]

        # Get linked items
        linked = await db.execute_fetchall(
            """SELECT i.id, i.korean, i.english, i.item_type, i.topik_level
               FROM sentence_items si
               JOIN items i ON i.id = si.item_id
               WHERE si.sentence_id = ?""",
            (sentence_id,)
        )
        linked_items = [{"id": li[0], "korean": li[1], "english": li[2],
                         "item_type": li[3], "topik_level": li[4]} for li in linked]

        return {
            "id": r[0], "korean": r[1], "english": r[2],
            "formality": r[3], "topik_level": r[4], "source": r[5],
            "notes": r[6], "created_at": r[7],
            "linked_items": linked_items,
        }
    finally:
        await db.close()


@router.post("", dependencies=[Depends(require_teacher)])
async def create_sentence(req: SentenceCreate):
    db = await get_db()
    try:
        english = req.english.strip()

        # Auto-translate if no English provided
        if not english:
            english = await chat_completion(
                "Translate the following Korean sentence to natural English. Return ONLY the English translation, nothing else.",
                req.korean
            )
            english = english.strip().strip('"')

        # Auto-link words to existing items (no AI — pure Python matching)
        matched_items = await find_matching_items(db, req.korean)
        linked_ids = [m["id"] for m in matched_items]

        # Auto-calculate TOPIK level if not provided
        topik_level = req.topik_level if req.topik_level else _estimate_sentence_level(matched_items)

        sentence_id = await insert_sentence(
            db, req.korean, english, req.formality, topik_level,
            source="teacher", notes=req.notes,
            linked_item_ids=linked_ids,
        )
        await db.commit()

        return {
            "id": sentence_id,
            "english": english,
            "linked_items": matched_items,
            "topik_level": topik_level,
        }
    finally:
        await db.close()


@router.post("/{sentence_id}/link/{item_id}", dependencies=[Depends(require_teacher)])
async def link_item(sentence_id: int, item_id: int):
    """Manually link an item to a sentence."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO sentence_items (sentence_id, item_id) VALUES (?, ?)",
            (sentence_id, item_id)
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/{sentence_id}/link/{item_id}", dependencies=[Depends(require_teacher)])
async def unlink_item(sentence_id: int, item_id: int):
    """Remove a link between an item and a sentence."""
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM sentence_items WHERE sentence_id = ? AND item_id = ?",
            (sentence_id, item_id)
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.get("/{sentence_id}/breakdown")
async def sentence_breakdown(sentence_id: int):
    """Word-by-word breakdown of a sentence, matching each token to items."""
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT korean, english, formality, topik_level FROM sentences WHERE id = ?",
            (sentence_id,)
        )
        if not rows:
            return JSONResponse({"error": "Not found"}, status_code=404)
        sentence_korean = rows[0][0]
        sentence_english = rows[0][1]
        formality = rows[0][2]
        topik_level = rows[0][3]

        # Get linked items for this sentence
        linked = await db.execute_fetchall(
            """SELECT i.id, i.korean, i.english, i.item_type, i.topik_level, i.pos, i.dictionary_form
               FROM sentence_items si
               JOIN items i ON i.id = si.item_id
               WHERE si.sentence_id = ?""",
            (sentence_id,)
        )
        items_map = {}
        for li in linked:
            items_map[li[0]] = {
                "id": li[0], "korean": li[1], "english": li[2],
                "item_type": li[3], "topik_level": li[4], "pos": li[5],
                "dictionary_form": li[6],
            }

        # Tokenize sentence into Korean words and non-Korean separators
        tokens = re.findall(r'[가-힣]+|[^가-힣]+', sentence_korean)

        # For each Korean token, try to match against linked items
        all_items = await db.execute_fetchall(
            "SELECT id, korean, dictionary_form, item_type, topik_level, pos, english FROM items"
        )

        breakdown = []
        for token in tokens:
            if not re.match(r'[가-힣]+', token):
                # Non-Korean token (space, punctuation)
                breakdown.append({"text": token, "type": "separator"})
                continue

            # Try to find a matching item
            best_match = None
            for item in all_items:
                item_korean = item[1].replace(" ", "")
                dict_form = (item[2] or "").replace(" ", "")
                # Check if the token contains or is contained in the item
                if token in item_korean or item_korean in token:
                    best_match = {
                        "id": item[0], "korean": item[1], "english": item[6],
                        "item_type": item[3], "topik_level": item[4], "pos": item[5],
                        "dictionary_form": item[2],
                        "linked": item[0] in items_map,
                    }
                    # Prefer exact matches
                    if token == item_korean:
                        break
                elif dict_form and (token in dict_form or dict_form in token):
                    best_match = {
                        "id": item[0], "korean": item[1], "english": item[6],
                        "item_type": item[3], "topik_level": item[4], "pos": item[5],
                        "dictionary_form": item[2],
                        "linked": item[0] in items_map,
                    }

            breakdown.append({
                "text": token,
                "type": "word",
                "match": best_match,
            })

        return {
            "sentence_id": sentence_id,
            "korean": sentence_korean,
            "english": sentence_english,
            "formality": formality,
            "topik_level": topik_level,
            "breakdown": breakdown,
        }
    finally:
        await db.close()


@router.delete("/{sentence_id}", dependencies=[Depends(require_teacher)])
async def delete_sentence(sentence_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM sentences WHERE id = ?", (sentence_id,))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()

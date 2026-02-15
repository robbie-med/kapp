from fastapi import APIRouter, Query, Depends, Request
from fastapi.responses import JSONResponse
from app.database import get_db, insert_item, insert_example
from app.models import ItemCreate, ItemUpdate, ExampleCreate
from app.auth import require_teacher, get_student_id
import json

router = APIRouter()


@router.get("")
async def list_items(
    request: Request,
    item_type: str = Query(None),
    topik_level: int = Query(None),
    search: str = Query(None),
    pos: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    db = await get_db()
    try:
        conditions = []
        params = []
        if item_type:
            conditions.append("item_type = ?")
            params.append(item_type)
        if topik_level:
            conditions.append("topik_level = ?")
            params.append(topik_level)
        if pos:
            conditions.append("pos = ?")
            params.append(pos)
        if search:
            conditions.append("(korean LIKE ? OR english LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * per_page

        count_row = await db.execute_fetchall(
            f"SELECT COUNT(*) as c FROM items {where}", params
        )
        total = count_row[0][0]

        rows = await db.execute_fetchall(
            f"""SELECT i.id, i.korean, i.english, i.item_type, i.topik_level, i.source, i.tags, i.notes,
                       i.pos, i.dictionary_form, i.grammar_category,
                       (SELECT COUNT(*) FROM examples e WHERE e.item_id = i.id) as example_count
                FROM items i {where} ORDER BY i.topik_level, i.korean
                LIMIT ? OFFSET ?""",
            params + [per_page, offset]
        )
        items = []
        for r in rows:
            items.append({
                "id": r[0], "korean": r[1], "english": r[2],
                "item_type": r[3], "topik_level": r[4], "source": r[5],
                "tags": json.loads(r[6]), "notes": r[7],
                "pos": r[8], "dictionary_form": r[9], "grammar_category": r[10],
                "example_count": r[11],
            })
        return {"items": items, "total": total, "page": page, "per_page": per_page}
    finally:
        await db.close()


@router.get("/{item_id}")
async def get_item(item_id: int, request: Request):
    student_id = get_student_id(request) or 1
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT id, korean, english, item_type, topik_level, source, tags, notes,
                      pos, dictionary_form, grammar_category
               FROM items WHERE id = ?""", (item_id,)
        )
        if not rows:
            return JSONResponse({"error": "Not found"}, status_code=404)
        r = rows[0]
        examples = await db.execute_fetchall(
            "SELECT id, korean, english, formality FROM examples WHERE item_id = ?",
            (item_id,)
        )
        mastery = await db.execute_fetchall(
            "SELECT grammar_score, vocab_score, formality_score, overall_score, practice_count FROM mastery WHERE item_id = ? AND student_id = ?",
            (item_id, student_id)
        )
        srs = await db.execute_fetchall(
            "SELECT ease_factor, interval_days, repetitions, next_review FROM srs_state WHERE item_id = ? AND student_id = ?",
            (item_id, student_id)
        )
        return {
            "id": r[0], "korean": r[1], "english": r[2],
            "item_type": r[3], "topik_level": r[4], "source": r[5],
            "tags": json.loads(r[6]), "notes": r[7],
            "pos": r[8], "dictionary_form": r[9], "grammar_category": r[10],
            "examples": [{"id": e[0], "korean": e[1], "english": e[2], "formality": e[3]} for e in examples],
            "mastery": dict(zip(["grammar_score", "vocab_score", "formality_score", "overall_score", "practice_count"], mastery[0])) if mastery else None,
            "srs": dict(zip(["ease_factor", "interval_days", "repetitions", "next_review"], srs[0])) if srs else None,
        }
    finally:
        await db.close()


@router.post("", dependencies=[Depends(require_teacher)])
async def create_item(item: ItemCreate):
    db = await get_db()
    try:
        item_id = await insert_item(
            db, item.korean, item.english, item.item_type,
            item.topik_level, item.source, item.tags, item.notes,
            pos=item.pos, dictionary_form=item.dictionary_form,
            grammar_category=item.grammar_category,
        )
        await db.commit()
        return {"id": item_id}
    finally:
        await db.close()


@router.put("/{item_id}", dependencies=[Depends(require_teacher)])
async def update_item(item_id: int, item: ItemUpdate):
    db = await get_db()
    try:
        # Build dynamic SET clause from non-None fields
        fields = {}
        if item.korean is not None:
            fields["korean"] = item.korean
        if item.english is not None:
            fields["english"] = item.english
        if item.item_type is not None:
            fields["item_type"] = item.item_type
        if item.topik_level is not None:
            fields["topik_level"] = item.topik_level
        if item.tags is not None:
            fields["tags"] = json.dumps(item.tags)
        if item.notes is not None:
            fields["notes"] = item.notes
        if item.pos is not None:
            fields["pos"] = item.pos
        if item.dictionary_form is not None:
            fields["dictionary_form"] = item.dictionary_form
        if item.grammar_category is not None:
            fields["grammar_category"] = item.grammar_category

        if not fields:
            return {"ok": True}

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [item_id]
        await db.execute(f"UPDATE items SET {set_clause} WHERE id = ?", values)
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.post("/{item_id}/examples", dependencies=[Depends(require_teacher)])
async def add_example(item_id: int, example: ExampleCreate):
    db = await get_db()
    try:
        await insert_example(db, item_id, example.korean, example.english, example.formality)
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/{item_id}/examples/{example_id}", dependencies=[Depends(require_teacher)])
async def delete_example(item_id: int, example_id: int):
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM examples WHERE id = ? AND item_id = ?",
            (example_id, item_id)
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/{item_id}", dependencies=[Depends(require_teacher)])
async def delete_item(item_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.get("/duplicates/find", dependencies=[Depends(require_teacher)])
async def find_duplicates():
    """Find potential duplicate items (exact korean match or same dictionary form)."""
    db = await get_db()
    try:
        # Find groups of items with identical korean text
        groups = []
        rows = await db.execute_fetchall(
            """SELECT korean, COUNT(*) as cnt
               FROM items GROUP BY korean HAVING cnt > 1
               ORDER BY cnt DESC"""
        )
        for r in rows:
            items = await db.execute_fetchall(
                """SELECT id, korean, english, item_type, topik_level, source, tags, notes,
                          pos, dictionary_form, grammar_category,
                          (SELECT COUNT(*) FROM examples e WHERE e.item_id = i.id) as example_count,
                          (SELECT SUM(practice_count) FROM mastery m WHERE m.item_id = i.id) as total_practices
                   FROM items i WHERE korean = ? ORDER BY id""",
                (r[0],)
            )
            groups.append({
                "match_type": "exact",
                "korean": r[0],
                "items": [{
                    "id": ir[0], "korean": ir[1], "english": ir[2],
                    "item_type": ir[3], "topik_level": ir[4], "source": ir[5],
                    "tags": json.loads(ir[6]), "notes": ir[7],
                    "pos": ir[8], "dictionary_form": ir[9], "grammar_category": ir[10],
                    "example_count": ir[11] or 0, "total_practices": ir[12] or 0,
                } for ir in items],
            })

        # Find items with same dictionary_form (different surface forms)
        dict_rows = await db.execute_fetchall(
            """SELECT dictionary_form, COUNT(*) as cnt
               FROM items WHERE dictionary_form IS NOT NULL AND dictionary_form != ''
               GROUP BY dictionary_form HAVING cnt > 1
               ORDER BY cnt DESC"""
        )
        seen_ids = {item["id"] for g in groups for item in g["items"]}
        for r in dict_rows:
            items = await db.execute_fetchall(
                """SELECT id, korean, english, item_type, topik_level, source, tags, notes,
                          pos, dictionary_form, grammar_category,
                          (SELECT COUNT(*) FROM examples e WHERE e.item_id = i.id) as example_count,
                          (SELECT SUM(practice_count) FROM mastery m WHERE m.item_id = i.id) as total_practices
                   FROM items i WHERE dictionary_form = ? ORDER BY id""",
                (r[0],)
            )
            item_list = [{
                "id": ir[0], "korean": ir[1], "english": ir[2],
                "item_type": ir[3], "topik_level": ir[4], "source": ir[5],
                "tags": json.loads(ir[6]), "notes": ir[7],
                "pos": ir[8], "dictionary_form": ir[9], "grammar_category": ir[10],
                "example_count": ir[11] or 0, "total_practices": ir[12] or 0,
            } for ir in items]
            # Skip if all items in this group were already covered by exact match
            if all(item["id"] in seen_ids for item in item_list):
                continue
            groups.append({
                "match_type": "dictionary_form",
                "korean": r[0],
                "items": item_list,
            })

        return {"groups": groups, "total_groups": len(groups)}
    finally:
        await db.close()


@router.post("/{keep_id}/merge/{remove_id}", dependencies=[Depends(require_teacher)])
async def merge_items(keep_id: int, remove_id: int):
    """Merge remove_id into keep_id: transfer examples and sentence links, then delete."""
    if keep_id == remove_id:
        return JSONResponse({"error": "Cannot merge item with itself"}, status_code=400)
    db = await get_db()
    try:
        # Verify both exist
        keep = await db.execute_fetchall("SELECT id FROM items WHERE id = ?", (keep_id,))
        remove = await db.execute_fetchall("SELECT id FROM items WHERE id = ?", (remove_id,))
        if not keep or not remove:
            return JSONResponse({"error": "Item not found"}, status_code=404)

        # Transfer examples
        await db.execute(
            "UPDATE examples SET item_id = ? WHERE item_id = ?",
            (keep_id, remove_id)
        )
        # Transfer sentence links (ignore conflicts if both items linked to same sentence)
        await db.execute(
            "UPDATE OR IGNORE sentence_items SET item_id = ? WHERE item_id = ?",
            (keep_id, remove_id)
        )
        # Clean up any remaining sentence_items for removed item
        await db.execute("DELETE FROM sentence_items WHERE item_id = ?", (remove_id,))
        # Delete the duplicate
        await db.execute("DELETE FROM items WHERE id = ?", (remove_id,))
        await db.commit()
        return {"ok": True, "kept": keep_id, "removed": remove_id}
    finally:
        await db.close()

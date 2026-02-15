"""Verify and fix item data in the database.

Usage:
    python scripts/verify_and_fix.py          # Dry run — show what would change
    python scripts/verify_and_fix.py --fix    # Apply fixes
    python scripts/verify_and_fix.py --dedup  # Remove duplicates (keeps lowest ID)
"""

import asyncio
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db, get_db

# POS tags derivable from item tags
TAG_TO_POS = {
    "noun": "noun", "verb": "verb", "adjective": "adjective",
    "adverb": "adverb", "particle": "particle", "determiner": "determiner",
    "interjection": "interjection", "suffix": "suffix",
}

# Verb/adjective endings for POS inference
VERB_ENDINGS = ("하다", "되다", "가다", "오다", "먹다", "마시다", "보다", "읽다",
                "쓰다", "듣다", "말하다", "주다", "받다", "알다", "모르다", "만들다",
                "나다", "서다", "앉다", "타다", "내다", "걷다", "뛰다", "자다",
                "일어나다", "시키다", "치다", "놓다", "넣다", "빼다")

ADJ_ENDINGS = ("있다", "없다", "이다", "크다", "작다", "많다", "적다", "좋다",
               "나쁘다", "길다", "짧다", "높다", "낮다", "넓다", "좁다",
               "같다", "다르다", "쉽다", "어렵다", "새롭다", "빠르다", "느리다")


def infer_pos(korean: str, tags: list[str]) -> str | None:
    """Infer POS from tags or word endings."""
    # Check tags first
    for tag in tags:
        if tag.lower() in TAG_TO_POS:
            return TAG_TO_POS[tag.lower()]
    # Infer from endings
    if any(korean.endswith(e) for e in VERB_ENDINGS) or korean.endswith("다") and "하" in korean:
        return "verb"
    if any(korean.endswith(e) for e in ADJ_ENDINGS):
        return "adjective"
    if korean.endswith("다"):
        return "verb"  # Default for -다 words
    return None


async def verify_and_fix(fix=False, dedup=False):
    await init_db()
    db = await get_db()

    try:
        rows = await db.execute_fetchall(
            "SELECT id, korean, english, item_type, topik_level, tags, pos, dictionary_form, source FROM items ORDER BY id"
        )

        print(f"Total items: {len(rows)}")

        # --- POS fixes ---
        pos_fixes = 0
        for r in rows:
            item_id, korean, english, item_type, topik_level = r[0], r[1], r[2], r[3], r[4]
            tags = json.loads(r[5]) if r[5] else []
            current_pos = r[6]

            if item_type != "vocab" or current_pos:
                continue

            inferred = infer_pos(korean, tags)
            if inferred:
                pos_fixes += 1
                if fix:
                    await db.execute("UPDATE items SET pos = ? WHERE id = ?", (inferred, item_id))

        print(f"POS fixes: {pos_fixes} items need POS" + (" (APPLIED)" if fix else " (dry run)"))

        # --- Duplicate detection ---
        korean_groups = {}
        for r in rows:
            korean = r[1]
            if korean not in korean_groups:
                korean_groups[korean] = []
            korean_groups[korean].append(r)

        dup_groups = {k: v for k, v in korean_groups.items() if len(v) > 1}
        total_dups = sum(len(v) - 1 for v in dup_groups.values())

        print(f"Duplicate groups: {len(dup_groups)} ({total_dups} items to remove)")

        if dedup and dup_groups:
            removed = 0
            for korean, items in dup_groups.items():
                # Keep the one with lowest ID (original)
                keep = items[0]
                for dup in items[1:]:
                    dup_id = dup[0]
                    keep_id = keep[0]
                    # Transfer examples
                    await db.execute(
                        "UPDATE examples SET item_id = ? WHERE item_id = ?",
                        (keep_id, dup_id)
                    )
                    # Transfer sentence links
                    await db.execute(
                        "UPDATE OR IGNORE sentence_items SET item_id = ? WHERE item_id = ?",
                        (keep_id, dup_id)
                    )
                    await db.execute("DELETE FROM sentence_items WHERE item_id = ?", (dup_id,))
                    # Delete duplicate
                    await db.execute("DELETE FROM items WHERE id = ?", (dup_id,))
                    removed += 1
            print(f"Removed {removed} duplicate items")

        # --- TOPIK level distribution ---
        level_dist = Counter()
        for r in rows:
            level_dist[r[4]] += 1
        print(f"Items by TOPIK level: {dict(sorted(level_dist.items()))}")

        # --- Summary ---
        type_dist = Counter()
        pos_dist = Counter()
        source_dist = Counter()
        for r in rows:
            type_dist[r[3]] += 1
            pos_dist[r[6] or "unset"] += 1
            source_dist[r[8] or "unknown"] += 1

        print(f"By type: {dict(type_dist)}")
        print(f"By POS: {dict(sorted(pos_dist.items()))}")
        print(f"By source: {dict(source_dist)}")

        if fix or dedup:
            await db.commit()
            print("\nChanges committed.")
        else:
            print("\nDry run. Use --fix to apply POS fixes, --dedup to remove duplicates.")

    finally:
        await db.close()


if __name__ == "__main__":
    fix = "--fix" in sys.argv
    dedup = "--dedup" in sys.argv
    asyncio.run(verify_and_fix(fix=fix, dedup=dedup))

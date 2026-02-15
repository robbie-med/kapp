"""Seed the database with TOPIK vocabulary and grammar points.

Usage:
    python scripts/seed_db.py          # Only seeds if DB is empty
    python scripts/seed_db.py --merge  # Add new items from seed files, skip existing
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db, get_db, insert_item, check_duplicate_item


# Derive POS from tags if not explicitly set
TAG_TO_POS = {
    "noun": "noun", "verb": "verb", "adjective": "adjective",
    "adverb": "adverb", "particle": "particle", "determiner": "determiner",
    "interjection": "interjection", "suffix": "suffix",
}

TAG_TO_GRAMMAR_CAT = {
    "ending": "ending", "particle": "particle", "connector": "connector",
    "expression": "expression", "conjugation": "conjugation",
}


def _derive_pos(item: dict) -> str | None:
    if item.get("pos"):
        return item["pos"]
    for tag in item.get("tags", []):
        if tag.lower() in TAG_TO_POS:
            return TAG_TO_POS[tag.lower()]
    return None


def _derive_grammar_category(item: dict) -> str | None:
    if item.get("grammar_category"):
        return item["grammar_category"]
    for tag in item.get("tags", []):
        if tag.lower() in TAG_TO_GRAMMAR_CAT:
            return TAG_TO_GRAMMAR_CAT[tag.lower()]
    return None


async def seed(merge=False):
    await init_db()
    db = await get_db()

    try:
        count = await db.execute_fetchall("SELECT COUNT(*) FROM items")
        existing = count[0][0]

        if existing > 0 and not merge:
            print(f"Database already has {existing} items. Skipping seed.")
            print("Use --merge to add new items without duplicating, or delete data/korean_app.db to re-seed.")
            return

        seed_dir = Path(__file__).resolve().parent.parent / "data" / "seed"
        added = 0
        skipped = 0

        # Seed vocab
        vocab_path = seed_dir / "topik_vocab.json"
        if vocab_path.exists():
            vocab = json.loads(vocab_path.read_text())
            for item in vocab:
                if merge:
                    dup = await check_duplicate_item(db, item["korean"])
                    if dup:
                        skipped += 1
                        continue
                await insert_item(
                    db, item["korean"], item["english"],
                    "vocab", item.get("topik_level", 1),
                    "seed", item.get("tags", []),
                    pos=_derive_pos(item),
                    dictionary_form=item.get("dictionary_form"),
                )
                added += 1
            print(f"Vocab: {added} added" + (f", {skipped} skipped (already exist)" if merge else ""))
        else:
            print(f"Warning: {vocab_path} not found")

        # Seed grammar
        grammar_added = 0
        grammar_skipped = 0
        grammar_path = seed_dir / "grammar_points.json"
        if grammar_path.exists():
            grammar = json.loads(grammar_path.read_text())
            for item in grammar:
                if merge:
                    dup = await check_duplicate_item(db, item["korean"])
                    if dup:
                        grammar_skipped += 1
                        continue
                await insert_item(
                    db, item["korean"], item["english"],
                    "grammar", item.get("topik_level", 1),
                    "seed", item.get("tags", []),
                    item.get("notes", ""),
                    grammar_category=_derive_grammar_category(item),
                )
                grammar_added += 1
            print(f"Grammar: {grammar_added} added" + (f", {grammar_skipped} skipped (already exist)" if merge else ""))
        else:
            print(f"Warning: {grammar_path} not found")

        await db.commit()
        total_added = added + grammar_added
        total_skipped = skipped + grammar_skipped
        print(f"\nSeeding complete! Added {total_added} items." + (f" Skipped {total_skipped} existing." if merge else ""))
    finally:
        await db.close()


if __name__ == "__main__":
    merge = "--merge" in sys.argv
    asyncio.run(seed(merge=merge))

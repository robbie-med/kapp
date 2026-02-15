#!/usr/bin/env python3
"""
Scrape curriculum structure from HowToStudyKorean.com and populate database.
This creates the curriculum framework that students can browse and practice from.
"""

import asyncio
import aiosqlite
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import DATABASE_PATH
from app.database import get_db

# Curriculum structure (manually defined based on website structure)
# Each unit has lessons with their URLs
CURRICULUM = {
    "Unit 0": {
        "number": 0,
        "title": "Pronunciation & Reading",
        "description": "Korean alphabet (Hangul), pronunciation rules, and basic reading",
        "topik_level": 1,
        "url": "https://www.howtostudykorean.com/unit0/",
        "lessons": []  # Skip Unit 0 for now (alphabet/pronunciation)
    },
    "Unit 1": {
        "number": 1,
        "title": "Basic Korean Grammar",
        "description": "Foundational grammar concepts, basic sentences, particles, conjugation",
        "topik_level": 1,
        "url": "https://www.howtostudykorean.com/unit1/",
        "lessons": [
            {"number": 1, "title": "Basic Korean Sentences", "url": "https://www.howtostudykorean.com/?page_id=279"},
            {"number": 2, "title": "Korean Particles", "url": "https://www.howtostudykorean.com/?page_id=281"},
            {"number": 3, "title": "Verbs and Adjectives", "url": "https://www.howtostudykorean.com/?page_id=283"},
            {"number": 4, "title": "Modifying Adjectives", "url": "https://www.howtostudykorean.com/?page_id=286"},
            {"number": 5, "title": "Conjugation", "url": "https://www.howtostudykorean.com/?page_id=289"},
            {"number": 6, "title": "Politeness Levels", "url": "https://www.howtostudykorean.com/?page_id=291"},
            {"number": 7, "title": "Irregulars", "url": "https://www.howtostudykorean.com/?page_id=294"},
            {"number": 8, "title": "Adverbs and Negation", "url": "https://www.howtostudykorean.com/?page_id=297"},
            {"number": 9, "title": "Korean Counters", "url": "https://www.howtostudykorean.com/?page_id=300"},
            {"number": 10, "title": "Korean Numbers", "url": "https://www.howtostudykorean.com/?page_id=302"},
            {"number": 11, "title": "Time", "url": "https://www.howtostudykorean.com/?page_id=304"},
            {"number": 12, "title": "More Irregulars", "url": "https://www.howtostudykorean.com/?page_id=306"},
            {"number": 13, "title": "Passive Verbs", "url": "https://www.howtostudykorean.com/?page_id=308"},
            {"number": 14, "title": "Questions", "url": "https://www.howtostudykorean.com/?page_id=310"},
            {"number": 15, "title": "More Questions", "url": "https://www.howtostudykorean.com/?page_id=312"},
            {"number": 16, "title": "Imperative", "url": "https://www.howtostudykorean.com/?page_id=314"},
            {"number": 17, "title": "Connecting Particles", "url": "https://www.howtostudykorean.com/?page_id=316"},
            {"number": 18, "title": "이다 Irregulars", "url": "https://www.howtostudykorean.com/?page_id=318"},
            {"number": 19, "title": "When, While, If", "url": "https://www.howtostudykorean.com/?page_id=320"},
            {"number": 20, "title": "Location Particles", "url": "https://www.howtostudykorean.com/?page_id=322"},
            {"number": 21, "title": "Describing Nouns", "url": "https://www.howtostudykorean.com/?page_id=324"},
            {"number": 22, "title": "More Connecting", "url": "https://www.howtostudykorean.com/?page_id=326"},
            {"number": 23, "title": "Want To", "url": "https://www.howtostudykorean.com/?page_id=328"},
            {"number": 24, "title": "And, Also, But", "url": "https://www.howtostudykorean.com/?page_id=330"},
            {"number": 25, "title": "Question Words", "url": "https://www.howtostudykorean.com/?page_id=332"},
        ]
    },
    "Unit 2": {
        "number": 2,
        "title": "Lower Intermediate Korean Grammar",
        "description": "More complex grammar structures, honorifics, compound sentences",
        "topik_level": 2,
        "url": "https://www.howtostudykorean.com/unit2/",
        "lessons": [
            {"number": 26, "title": "Honorifics", "url": "https://www.howtostudykorean.com/?page_id=392"},
            {"number": 27, "title": "Describing Verbs", "url": "https://www.howtostudykorean.com/?page_id=395"},
            {"number": 28, "title": "Ability and Possibility", "url": "https://www.howtostudykorean.com/?page_id=397"},
            {"number": 29, "title": "Making Suggestions", "url": "https://www.howtostudykorean.com/?page_id=399"},
            {"number": 30, "title": "Shouldn't/Don't Have To", "url": "https://www.howtostudykorean.com/?page_id=401"},
            # Add more Unit 2 lessons as needed
        ]
    },
    # Can expand to Unit 3-8 later
}


async def populate_curriculum():
    """Insert curriculum structure into database."""
    db = await get_db()
    try:
        print("📚 Populating curriculum structure...")

        for unit_key, unit_data in CURRICULUM.items():
            if not unit_data["lessons"]:
                print(f"⏭️  Skipping {unit_key} (no lessons defined)")
                continue

            # Insert unit
            cursor = await db.execute(
                """INSERT INTO curriculum_units (unit_number, title, description, topik_level, url, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(unit_number) DO UPDATE SET
                       title=excluded.title,
                       description=excluded.description,
                       topik_level=excluded.topik_level,
                       url=excluded.url""",
                (unit_data["number"], unit_data["title"], unit_data["description"],
                 unit_data["topik_level"], unit_data["url"], unit_data["number"])
            )
            unit_id = cursor.lastrowid

            # Get unit_id if it already existed
            if unit_id == 0:
                rows = await db.execute_fetchall(
                    "SELECT id FROM curriculum_units WHERE unit_number = ?",
                    (unit_data["number"],)
                )
                unit_id = rows[0][0]

            print(f"✅ {unit_key}: {unit_data['title']} (ID: {unit_id})")

            # Insert lessons
            for lesson in unit_data["lessons"]:
                await db.execute(
                    """INSERT INTO curriculum_lessons (unit_id, lesson_number, title, url, sort_order)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(unit_id, lesson_number) DO UPDATE SET
                           title=excluded.title,
                           url=excluded.url""",
                    (unit_id, lesson["number"], lesson["title"], lesson["url"], lesson["number"])
                )
                print(f"   📖 Lesson {lesson['number']}: {lesson['title']}")

        await db.commit()
        print(f"\n✅ Curriculum structure populated!")

        # Show summary
        units = await db.execute_fetchall("SELECT COUNT(*) FROM curriculum_units")
        lessons = await db.execute_fetchall("SELECT COUNT(*) FROM curriculum_lessons")
        print(f"   {units[0][0]} units, {lessons[0][0]} lessons")

    finally:
        await db.close()


async def match_items_to_lessons():
    """
    Auto-match existing items to lessons based on TOPIK level and keywords.
    This creates initial lesson_items linkages.
    """
    db = await get_db()
    try:
        print("\n🔗 Matching items to lessons...")

        # Strategy: For now, just match by TOPIK level
        # Unit 1 (TOPIK 1) → Items with topik_level = 1
        # Unit 2 (TOPIK 2) → Items with topik_level = 2

        lessons = await db.execute_fetchall(
            """SELECT l.id, l.lesson_number, u.topik_level
               FROM curriculum_lessons l
               JOIN curriculum_units u ON u.id = l.unit_id
               ORDER BY l.id"""
        )

        for lesson_id, lesson_num, topik_level in lessons:
            # Get items for this TOPIK level
            items = await db.execute_fetchall(
                "SELECT id FROM items WHERE topik_level = ? LIMIT 10",
                (topik_level,)
            )

            if items:
                for idx, (item_id,) in enumerate(items):
                    await db.execute(
                        """INSERT OR IGNORE INTO lesson_items (lesson_id, item_id, is_primary, introduced_order)
                           VALUES (?, ?, ?, ?)""",
                        (lesson_id, item_id, 1, idx + 1)
                    )
                print(f"   ✅ Lesson {lesson_num}: Linked {len(items)} items")

        await db.commit()

        # Show summary
        linked = await db.execute_fetchall("SELECT COUNT(*) FROM lesson_items")
        print(f"\n✅ Linked {linked[0][0]} items to lessons")
        print("   (This is a basic auto-match. You can refine mappings later.)")

    finally:
        await db.close()


async def main():
    print("🚀 HowToStudyKorean.com Curriculum Importer\n")

    # Step 1: Populate structure
    await populate_curriculum()

    # Step 2: Auto-match items
    await match_items_to_lessons()

    print("\n✅ Done! Curriculum is ready to use.")
    print("   Students can now browse lessons and practice specific content.")


if __name__ == "__main__":
    asyncio.run(main())

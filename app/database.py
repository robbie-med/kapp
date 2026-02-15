import aiosqlite
import json
import os
from pathlib import Path
from app.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    korean TEXT NOT NULL,
    english TEXT NOT NULL,
    item_type TEXT NOT NULL DEFAULT 'vocab',  -- 'vocab' or 'grammar'
    topik_level INTEGER DEFAULT 1,
    source TEXT DEFAULT 'seed',  -- 'seed', 'telegram', 'signal', 'manual'
    tags TEXT DEFAULT '[]',  -- JSON array
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    korean TEXT NOT NULL,
    english TEXT NOT NULL,
    formality TEXT DEFAULT 'polite',  -- 'formal', 'polite', 'casual'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS srs_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE REFERENCES items(id) ON DELETE CASCADE,
    ease_factor REAL DEFAULT 2.5,
    interval_days REAL DEFAULT 0,
    repetitions INTEGER DEFAULT 0,
    next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_reviewed TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS practice_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_ids TEXT NOT NULL DEFAULT '[]',  -- JSON array of item IDs
    prompt TEXT NOT NULL,
    formality TEXT DEFAULT 'polite',
    audio_path TEXT,
    transcript TEXT,
    overall_score REAL,
    feedback_json TEXT,  -- full AI feedback
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE REFERENCES items(id) ON DELETE CASCADE,
    grammar_score REAL DEFAULT 0,
    vocab_score REAL DEFAULT 0,
    formality_score REAL DEFAULT 0,
    overall_score REAL DEFAULT 0,
    practice_count INTEGER DEFAULT 0,
    last_practiced TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_srs_next_review ON srs_state(next_review);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type);
CREATE INDEX IF NOT EXISTS idx_items_level ON items(topik_level);
CREATE INDEX IF NOT EXISTS idx_mastery_overall ON mastery(overall_score);
"""

# --- Schema migrations ---
# Each entry is run once, in order. Version tracked in settings table.

MIGRATIONS = [
    # Migration 1: Multi-student profiles + Item taxonomy
    """
    -- Students table
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Recreate srs_state with student_id (SQLite can't alter UNIQUE constraints)
    CREATE TABLE IF NOT EXISTS srs_state_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL DEFAULT 1 REFERENCES students(id) ON DELETE CASCADE,
        ease_factor REAL DEFAULT 2.5,
        interval_days REAL DEFAULT 0,
        repetitions INTEGER DEFAULT 0,
        next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_reviewed TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(item_id, student_id)
    );

    -- Recreate mastery with student_id
    CREATE TABLE IF NOT EXISTS mastery_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL DEFAULT 1 REFERENCES students(id) ON DELETE CASCADE,
        grammar_score REAL DEFAULT 0,
        vocab_score REAL DEFAULT 0,
        formality_score REAL DEFAULT 0,
        overall_score REAL DEFAULT 0,
        practice_count INTEGER DEFAULT 0,
        last_practiced TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(item_id, student_id)
    );

    -- Recreate settings with student_id (0 = global, >0 = student-specific)
    CREATE TABLE IF NOT EXISTS settings_new (
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        student_id INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (key, student_id)
    );
    """,
    # Migration 2: Sentences, encounters, student level tracking
    """
    -- Standalone sentences (not tied to a single item)
    CREATE TABLE IF NOT EXISTS sentences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        korean TEXT NOT NULL,
        english TEXT NOT NULL DEFAULT '',
        formality TEXT DEFAULT 'polite',
        topik_level INTEGER DEFAULT 1,
        source TEXT DEFAULT 'teacher',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Many-to-many: which items appear in which sentences
    CREATE TABLE IF NOT EXISTS sentence_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sentence_id INTEGER NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
        item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
        UNIQUE(sentence_id, item_id)
    );

    -- Track when each student first encounters and practices each item
    CREATE TABLE IF NOT EXISTS encounters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        first_practiced TIMESTAMP,
        encounter_count INTEGER DEFAULT 1,
        UNIQUE(student_id, item_id)
    );

    -- Student TOPIK level over time
    CREATE TABLE IF NOT EXISTS student_level_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        estimated_level REAL NOT NULL,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_sentences_level ON sentences(topik_level);
    CREATE INDEX IF NOT EXISTS idx_sentence_items_sentence ON sentence_items(sentence_id);
    CREATE INDEX IF NOT EXISTS idx_sentence_items_item ON sentence_items(item_id);
    CREATE INDEX IF NOT EXISTS idx_encounters_student ON encounters(student_id);
    CREATE INDEX IF NOT EXISTS idx_level_history_student ON student_level_history(student_id, calculated_at);
    """,
    # Migration 3: Curriculum, goals, study time, practice modes
    """
    -- Curriculum state: tracks each student's position in the TOPIK progression
    CREATE TABLE IF NOT EXISTS curriculum_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        current_topik_level INTEGER NOT NULL DEFAULT 1,
        current_position INTEGER NOT NULL DEFAULT 0,
        items_introduced INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id)
    );

    -- Goals table: student-set goals with deadlines
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        goal_type TEXT NOT NULL,
        target_value INTEGER NOT NULL,
        current_value INTEGER NOT NULL DEFAULT 0,
        period TEXT NOT NULL DEFAULT 'custom',
        deadline TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE INDEX IF NOT EXISTS idx_goals_student ON goals(student_id, active);
    CREATE INDEX IF NOT EXISTS idx_curriculum_student ON curriculum_state(student_id);
    """,
    # Migration 4: Comprehensive item tracking for weakness analysis
    """
    -- Add tracking columns to mastery table (exposure, usage, errors)
    -- Note: These will be added via ALTER TABLE in _run_migration_4

    -- Add encounter_type to encounters table for granular tracking
    -- Note: This will be added via ALTER TABLE in _run_migration_4
    """,
    # Migration 5: Curriculum structure (HowToStudyKorean.com integration)
    """
    -- Curriculum units (e.g., Unit 1, Unit 2)
    CREATE TABLE IF NOT EXISTS curriculum_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        topik_level INTEGER,
        url TEXT,
        sort_order INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(unit_number)
    );

    -- Lessons within units
    CREATE TABLE IF NOT EXISTS curriculum_lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id INTEGER NOT NULL REFERENCES curriculum_units(id) ON DELETE CASCADE,
        lesson_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        url TEXT,
        description TEXT,
        sort_order INTEGER,
        estimated_hours REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(unit_id, lesson_number)
    );

    -- Link items to lessons (which lesson introduces this item)
    CREATE TABLE IF NOT EXISTS lesson_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER NOT NULL REFERENCES curriculum_lessons(id) ON DELETE CASCADE,
        item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
        is_primary BOOLEAN DEFAULT 1,
        introduced_order INTEGER,
        UNIQUE(lesson_id, item_id)
    );

    -- Student progress through lessons
    CREATE TABLE IF NOT EXISTS lesson_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        lesson_id INTEGER NOT NULL REFERENCES curriculum_lessons(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'available',
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        mastery_score REAL DEFAULT 0.0,
        practice_count INTEGER DEFAULT 0,
        last_practiced TIMESTAMP,
        UNIQUE(student_id, lesson_id)
    );

    CREATE INDEX IF NOT EXISTS idx_units_number ON curriculum_units(unit_number);
    CREATE INDEX IF NOT EXISTS idx_lessons_unit ON curriculum_lessons(unit_id, sort_order);
    CREATE INDEX IF NOT EXISTS idx_lesson_items_lesson ON lesson_items(lesson_id);
    CREATE INDEX IF NOT EXISTS idx_lesson_items_item ON lesson_items(item_id);
    CREATE INDEX IF NOT EXISTS idx_lesson_progress_student ON lesson_progress(student_id, lesson_id);
    """,
    # Migration 6: Calendar/curriculum assignments for teacher-student planning
    """
    -- Teacher can assign lessons/sentences/vocab to students with due dates
    CREATE TABLE IF NOT EXISTS curriculum_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        teacher_id INTEGER DEFAULT 1,
        assignment_type TEXT NOT NULL CHECK(assignment_type IN ('lesson', 'sentence', 'vocab')),
        lesson_id INTEGER REFERENCES curriculum_lessons(id) ON DELETE CASCADE,
        sentence_id INTEGER REFERENCES sentences(id) ON DELETE SET NULL,
        item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
        assigned_date DATE NOT NULL DEFAULT (date('now')),
        due_date DATE NOT NULL,
        completed_at DATETIME,
        notes TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_assignments_student ON curriculum_assignments(student_id, due_date);
    CREATE INDEX IF NOT EXISTS idx_assignments_completed ON curriculum_assignments(completed_at);
    CREATE INDEX IF NOT EXISTS idx_assignments_type ON curriculum_assignments(assignment_type);
    """,
]

# Post-migration Python logic (runs after SQL for each migration index)
async def _run_migration_1(db):
    """Backfill data for migration 1. Handles partially-completed state."""
    # Create default student from APP_PASSWORD_HASH env var
    old_hash = os.getenv("APP_PASSWORD_HASH", "")
    await db.execute(
        "INSERT OR IGNORE INTO students (id, username, display_name, password_hash) VALUES (1, 'student', 'Student', ?)",
        (old_hash,)
    )

    # Check which tables exist to handle partial migration
    tables = await db.execute_fetchall(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    table_names = {t[0] for t in tables}

    # Migrate srs_state → srs_state_new → srs_state
    if "srs_state_new" in table_names and "srs_state" in table_names:
        # Check if old srs_state has student_id column already
        cols = await db.execute_fetchall("PRAGMA table_info(srs_state)")
        col_names = {c[1] for c in cols}
        if "student_id" not in col_names:
            # Old table, copy data to new
            await db.execute(
                """INSERT OR IGNORE INTO srs_state_new (id, item_id, student_id, ease_factor, interval_days, repetitions, next_review, last_reviewed, created_at)
                   SELECT id, item_id, 1, ease_factor, interval_days, repetitions, next_review, last_reviewed, created_at FROM srs_state"""
            )
            await db.execute("DROP TABLE srs_state")
            await db.execute("ALTER TABLE srs_state_new RENAME TO srs_state")
        else:
            # Already migrated, just clean up _new
            await db.execute("DROP TABLE IF EXISTS srs_state_new")
    elif "srs_state_new" in table_names:
        await db.execute("ALTER TABLE srs_state_new RENAME TO srs_state")

    # Migrate mastery → mastery_new → mastery
    if "mastery_new" in table_names and "mastery" in table_names:
        cols = await db.execute_fetchall("PRAGMA table_info(mastery)")
        col_names = {c[1] for c in cols}
        if "student_id" not in col_names:
            await db.execute(
                """INSERT OR IGNORE INTO mastery_new (id, item_id, student_id, grammar_score, vocab_score, formality_score, overall_score, practice_count, last_practiced, updated_at)
                   SELECT id, item_id, 1, grammar_score, vocab_score, formality_score, overall_score, practice_count, last_practiced, updated_at FROM mastery"""
            )
            await db.execute("DROP TABLE mastery")
            await db.execute("ALTER TABLE mastery_new RENAME TO mastery")
        else:
            await db.execute("DROP TABLE IF EXISTS mastery_new")
    elif "mastery_new" in table_names:
        await db.execute("ALTER TABLE mastery_new RENAME TO mastery")

    # Migrate settings → settings_new → settings
    if "settings_new" in table_names and "settings" in table_names:
        cols = await db.execute_fetchall("PRAGMA table_info(settings)")
        col_names = {c[1] for c in cols}
        if "student_id" not in col_names:
            await db.execute(
                "INSERT OR IGNORE INTO settings_new (key, value, student_id) SELECT key, value, 0 FROM settings"
            )
            await db.execute("DROP TABLE settings")
            await db.execute("ALTER TABLE settings_new RENAME TO settings")
        else:
            await db.execute("DROP TABLE IF EXISTS settings_new")
    elif "settings_new" in table_names:
        await db.execute("ALTER TABLE settings_new RENAME TO settings")

    # Add student_id column to practice_log if not present
    cols = await db.execute_fetchall("PRAGMA table_info(practice_log)")
    col_names = {c[1] for c in cols}
    if "student_id" not in col_names:
        await db.execute("ALTER TABLE practice_log ADD COLUMN student_id INTEGER DEFAULT 1")
        await db.execute("UPDATE practice_log SET student_id = 1")

    # Add item taxonomy columns if not present
    cols = await db.execute_fetchall("PRAGMA table_info(items)")
    col_names = {c[1] for c in cols}
    if "pos" not in col_names:
        await db.execute("ALTER TABLE items ADD COLUMN pos TEXT")
    if "dictionary_form" not in col_names:
        await db.execute("ALTER TABLE items ADD COLUMN dictionary_form TEXT")
    if "grammar_category" not in col_names:
        await db.execute("ALTER TABLE items ADD COLUMN grammar_category TEXT")

    # Create indexes
    await db.execute("CREATE INDEX IF NOT EXISTS idx_srs_student_review ON srs_state(student_id, next_review)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_mastery_student ON mastery(student_id, overall_score)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_practice_log_student ON practice_log(student_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_items_pos ON items(pos)")

async def _run_migration_3(db):
    """Add duration_seconds, practice_mode, and sentence_id to practice_log."""
    cols = await db.execute_fetchall("PRAGMA table_info(practice_log)")
    col_names = {c[1] for c in cols}
    if "duration_seconds" not in col_names:
        await db.execute(
            "ALTER TABLE practice_log ADD COLUMN duration_seconds INTEGER"
        )
    if "practice_mode" not in col_names:
        await db.execute(
            "ALTER TABLE practice_log ADD COLUMN practice_mode TEXT DEFAULT 'speaking'"
        )
    if "sentence_id" not in col_names:
        await db.execute(
            "ALTER TABLE practice_log ADD COLUMN sentence_id INTEGER"
        )


async def _run_migration_4(db):
    """Add comprehensive tracking metrics for weakness analysis."""
    # Add columns to mastery table
    mastery_cols = await db.execute_fetchall("PRAGMA table_info(mastery)")
    mastery_col_names = {c[1] for c in mastery_cols}

    if "exposure_count" not in mastery_col_names:
        await db.execute(
            "ALTER TABLE mastery ADD COLUMN exposure_count INTEGER DEFAULT 0"
        )
    if "usage_count" not in mastery_col_names:
        await db.execute(
            "ALTER TABLE mastery ADD COLUMN usage_count INTEGER DEFAULT 0"
        )
    if "error_count" not in mastery_col_names:
        await db.execute(
            "ALTER TABLE mastery ADD COLUMN error_count INTEGER DEFAULT 0"
        )

    # Add encounter_type column to encounters table
    encounters_cols = await db.execute_fetchall("PRAGMA table_info(encounters)")
    encounters_col_names = {c[1] for c in encounters_cols}

    if "encounter_type" not in encounters_col_names:
        await db.execute(
            "ALTER TABLE encounters ADD COLUMN encounter_type TEXT DEFAULT 'exposed'"
        )

    # Backfill: Set exposure_count = practice_count for existing data
    await db.execute(
        "UPDATE mastery SET exposure_count = practice_count WHERE exposure_count = 0"
    )
    await db.execute(
        "UPDATE mastery SET usage_count = practice_count WHERE usage_count = 0"
    )


_MIGRATION_RUNNERS = {1: _run_migration_1, 3: _run_migration_3, 4: _run_migration_4}


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def _get_schema_version(db) -> int:
    try:
        rows = await db.execute_fetchall(
            "SELECT value FROM settings WHERE key = 'schema_version'"
        )
        if rows:
            return int(rows[0][0])
    except Exception:
        pass
    return 0


async def _run_migrations(db):
    current = await _get_schema_version(db)
    for i, migration_sql in enumerate(MIGRATIONS, start=1):
        if i > current:
            await db.executescript(migration_sql)
            # Run Python migration logic if any
            runner = _MIGRATION_RUNNERS.get(i)
            if runner:
                await runner(db)
            # Track version — settings table may or may not have student_id column
            try:
                await db.execute(
                    "INSERT OR REPLACE INTO settings (key, value, student_id) VALUES ('schema_version', ?, 0)",
                    (str(i),)
                )
            except Exception:
                # Fallback for old settings schema
                await db.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('schema_version', ?)",
                    (str(i),)
                )
            await db.commit()


async def init_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
        await _run_migrations(db)
    finally:
        await db.close()


async def get_setting(key: str, env_fallback: str = "", student_id=None) -> str:
    """Get a setting from DB, falling back to env_fallback."""
    try:
        db = await get_db()
        try:
            if student_id is not None:
                # Try student-specific first, then global fallback
                rows = await db.execute_fetchall(
                    "SELECT value FROM settings WHERE key = ? AND student_id = ?",
                    (key, student_id)
                )
                if rows and rows[0][0]:
                    return rows[0][0]
                # Fall through to global
            rows = await db.execute_fetchall(
                "SELECT value FROM settings WHERE key = ? AND student_id = 0",
                (key,)
            )
            if rows and rows[0][0]:
                return rows[0][0]
        finally:
            await db.close()
    except Exception:
        pass
    return env_fallback


async def set_setting(key: str, value: str, student_id: int = 0):
    """Write a setting to the DB."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value, student_id) VALUES (?, ?, ?)",
            (key, value, student_id)
        )
        await db.commit()
    finally:
        await db.close()


async def check_duplicate_item(db: aiosqlite.Connection, korean: str):
    """Return existing item (id, korean, english) if korean text matches, else None."""
    rows = await db.execute_fetchall(
        "SELECT id, korean, english FROM items WHERE korean = ?", (korean,)
    )
    return dict(rows[0]) if rows else None


async def delete_items_by_ids(db: aiosqlite.Connection, item_ids: list[int]) -> int:
    """Delete items by IDs. Returns count deleted."""
    if not item_ids:
        return 0
    placeholders = ",".join("?" for _ in item_ids)
    cursor = await db.execute(
        f"DELETE FROM items WHERE id IN ({placeholders})", item_ids
    )
    return cursor.rowcount


async def insert_item(db: aiosqlite.Connection, korean: str, english: str,
                      item_type: str = "vocab", topik_level: int = 1,
                      source: str = "seed", tags: list | None = None,
                      notes: str = "",
                      pos: str | None = None, dictionary_form: str | None = None,
                      grammar_category: str | None = None) -> int:
    tags = tags or []
    cursor = await db.execute(
        """INSERT INTO items (korean, english, item_type, topik_level, source, tags, notes,
                             pos, dictionary_form, grammar_category)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (korean, english, item_type, topik_level, source, json.dumps(tags), notes,
         pos, dictionary_form, grammar_category)
    )
    return cursor.lastrowid


async def ensure_student_item_state(db: aiosqlite.Connection, item_id: int, student_id: int):
    """Lazily create SRS + mastery rows for a student+item pair if they don't exist."""
    await db.execute(
        "INSERT OR IGNORE INTO srs_state (item_id, student_id) VALUES (?, ?)",
        (item_id, student_id)
    )
    await db.execute(
        "INSERT OR IGNORE INTO mastery (item_id, student_id) VALUES (?, ?)",
        (item_id, student_id)
    )


async def insert_sentence(db: aiosqlite.Connection, korean: str, english: str,
                          formality: str = "polite", topik_level: int = 1,
                          source: str = "teacher", notes: str = "",
                          linked_item_ids: list[int] | None = None) -> int:
    cursor = await db.execute(
        """INSERT INTO sentences (korean, english, formality, topik_level, source, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (korean, english, formality, topik_level, source, notes)
    )
    sentence_id = cursor.lastrowid
    if linked_item_ids:
        for item_id in linked_item_ids:
            await db.execute(
                "INSERT OR IGNORE INTO sentence_items (sentence_id, item_id) VALUES (?, ?)",
                (sentence_id, item_id)
            )
    return sentence_id


async def record_encounter(db: aiosqlite.Connection, student_id: int, item_id: int,
                           practiced: bool = False):
    """Record or update an encounter for a student+item pair."""
    if practiced:
        await db.execute(
            """INSERT INTO encounters (student_id, item_id, first_seen, first_practiced)
               VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
               ON CONFLICT(student_id, item_id) DO UPDATE SET
                   encounter_count = encounter_count + 1,
                   first_practiced = COALESCE(first_practiced, CURRENT_TIMESTAMP)""",
            (student_id, item_id)
        )
    else:
        await db.execute(
            """INSERT INTO encounters (student_id, item_id, first_seen)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(student_id, item_id) DO UPDATE SET
                   encounter_count = encounter_count + 1""",
            (student_id, item_id)
        )


async def record_encounter_with_type(db: aiosqlite.Connection, student_id: int, item_id: int,
                                     encounter_type: str):
    """
    Record an encounter with specific type for weakness tracking.
    encounter_type: 'exposed' | 'used_correctly' | 'used_incorrectly' | 'missing'
    """
    await db.execute(
        """INSERT INTO encounters (student_id, item_id, first_seen, first_practiced, encounter_type)
           VALUES (?, ?, CURRENT_TIMESTAMP,
                   CASE WHEN ? IN ('used_correctly', 'used_incorrectly') THEN CURRENT_TIMESTAMP ELSE NULL END,
                   ?)
           ON CONFLICT(student_id, item_id) DO UPDATE SET
               encounter_count = encounter_count + 1,
               first_practiced = COALESCE(first_practiced,
                   CASE WHEN ? IN ('used_correctly', 'used_incorrectly') THEN CURRENT_TIMESTAMP ELSE NULL END),
               encounter_type = ?""",
        (student_id, item_id, encounter_type, encounter_type, encounter_type, encounter_type)
    )


async def update_item_metrics(db: aiosqlite.Connection, student_id: int, item_id: int,
                              was_used: bool = False, was_error: bool = False):
    """
    Update mastery metrics for weakness tracking.
    - Increments exposure_count always
    - Increments usage_count if was_used=True
    - Increments error_count if was_error=True
    """
    await ensure_student_item_state(db, item_id, student_id)

    if was_used and was_error:
        await db.execute(
            """UPDATE mastery SET
                   exposure_count = exposure_count + 1,
                   usage_count = usage_count + 1,
                   error_count = error_count + 1
               WHERE item_id = ? AND student_id = ?""",
            (item_id, student_id)
        )
    elif was_used:
        await db.execute(
            """UPDATE mastery SET
                   exposure_count = exposure_count + 1,
                   usage_count = usage_count + 1
               WHERE item_id = ? AND student_id = ?""",
            (item_id, student_id)
        )
    else:
        await db.execute(
            """UPDATE mastery SET
                   exposure_count = exposure_count + 1
               WHERE item_id = ? AND student_id = ?""",
            (item_id, student_id)
        )


async def calculate_student_level(db: aiosqlite.Connection, student_id: int) -> float:
    """Calculate estimated TOPIK level from mastery scores. Returns e.g. 2.3."""
    rows = await db.execute_fetchall(
        """SELECT i.topik_level, m.overall_score, m.practice_count
           FROM mastery m
           JOIN items i ON i.id = m.item_id
           WHERE m.student_id = ? AND m.practice_count > 0""",
        (student_id,)
    )
    if not rows:
        return 1.0

    # Weighted score per level
    level_scores = {}  # level -> (total_weighted_score, total_weight)
    for topik_level, score, practice_count in rows:
        weight = min(practice_count, 10)  # cap weight at 10 practices
        if topik_level not in level_scores:
            level_scores[topik_level] = [0.0, 0.0]
        level_scores[topik_level][0] += score * weight
        level_scores[topik_level][1] += weight

    # Average mastery per level
    level_mastery = {}
    for level, (total_score, total_weight) in level_scores.items():
        level_mastery[level] = total_score / total_weight if total_weight else 0

    # Estimated level: highest level where mastery >= 0.5, plus fractional from next
    estimated = 1.0
    for level in sorted(level_mastery.keys()):
        mastery = level_mastery[level]
        if mastery >= 0.5:
            estimated = float(level)
            # Add fractional part from mastery above threshold
            estimated += (mastery - 0.5) * 1.0  # 0.5 mastery = .0, 1.0 mastery = +0.5
        else:
            # Partial credit for current level
            estimated = float(level - 1) + mastery
            break

    estimated = max(1.0, min(6.0, estimated))

    # Record in history
    await db.execute(
        "INSERT INTO student_level_history (student_id, estimated_level) VALUES (?, ?)",
        (student_id, round(estimated, 2))
    )

    return round(estimated, 2)


async def insert_example(db: aiosqlite.Connection, item_id: int,
                         korean: str, english: str,
                         formality: str = "polite"):
    await db.execute(
        """INSERT INTO examples (item_id, korean, english, formality)
           VALUES (?, ?, ?, ?)""",
        (item_id, korean, english, formality)
    )


async def get_curriculum_state(db: aiosqlite.Connection, student_id: int) -> dict | None:
    """Get curriculum progression state for a student."""
    rows = await db.execute_fetchall(
        """SELECT current_topik_level, current_position, items_introduced, updated_at
           FROM curriculum_state WHERE student_id = ?""",
        (student_id,)
    )
    if not rows:
        return None
    r = rows[0]
    return {
        "current_topik_level": r[0],
        "current_position": r[1],
        "items_introduced": r[2],
        "updated_at": r[3],
    }


async def upsert_curriculum_state(db: aiosqlite.Connection, student_id: int,
                                   topik_level: int, position: int, items_introduced: int):
    """Update or create curriculum state for a student."""
    await db.execute(
        """INSERT INTO curriculum_state (student_id, current_topik_level, current_position,
                                        items_introduced, updated_at)
           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(student_id) DO UPDATE SET
               current_topik_level = ?, current_position = ?,
               items_introduced = ?, updated_at = CURRENT_TIMESTAMP""",
        (student_id, topik_level, position, items_introduced,
         topik_level, position, items_introduced)
    )


async def get_sentences_for_items(db: aiosqlite.Connection, item_ids: list[int]) -> list[dict]:
    """Find sentences that contain ANY of the given item IDs, ordered by match count."""
    if not item_ids:
        return []
    placeholders = ",".join("?" for _ in item_ids)
    rows = await db.execute_fetchall(
        f"""SELECT DISTINCT s.id, s.korean, s.english, s.formality, s.topik_level,
                   (SELECT COUNT(*) FROM sentence_items si2
                    WHERE si2.sentence_id = s.id AND si2.item_id IN ({placeholders})) as match_count
            FROM sentences s
            JOIN sentence_items si ON si.sentence_id = s.id
            WHERE si.item_id IN ({placeholders})
            ORDER BY match_count DESC
            LIMIT 5""",
        item_ids + item_ids
    )
    return [{"id": r[0], "korean": r[1], "english": r[2],
             "formality": r[3], "topik_level": r[4], "match_count": r[5]} for r in rows]


def _extract_korean_words(text: str) -> list[str]:
    """Extract Korean character sequences from text."""
    import re
    return re.findall(r'[가-힣]+', text)


async def find_matching_items(db: aiosqlite.Connection, korean_sentence: str) -> list[dict]:
    """Match words in a Korean sentence to items by korean or dictionary_form.
    Returns list of dicts: [{"id": int, "korean": str, "item_type": str, "topik_level": int}, ...]
    """
    words = _extract_korean_words(korean_sentence)
    if not words:
        return []

    # Get all items for matching (korean field + dictionary_form)
    rows = await db.execute_fetchall(
        "SELECT id, korean, dictionary_form, item_type, topik_level FROM items"
    )

    matched = []
    seen_ids = set()
    for row in rows:
        item_id, korean, dict_form, item_type, topik_level = row[0], row[1], row[2], row[3], row[4]
        if item_id in seen_ids:
            continue
        # Check if item's korean or dictionary_form appears in the sentence
        item_korean_clean = korean.replace(" ", "")
        for word in words:
            if word in item_korean_clean or item_korean_clean in word:
                matched.append({"id": item_id, "korean": korean, "item_type": item_type, "topik_level": topik_level})
                seen_ids.add(item_id)
                break
        if item_id not in seen_ids and dict_form:
            dict_clean = dict_form.replace(" ", "")
            for word in words:
                if word in dict_clean or dict_clean in word:
                    matched.append({"id": item_id, "korean": korean, "item_type": item_type, "topik_level": topik_level})
                    seen_ids.add(item_id)
                    break

    return matched

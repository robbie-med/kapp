# Implementation Plan: 6 New Features

## Overview
Six features to add: (A) teacher sentences/assigned items in practice, (B) TOPIK curriculum progression, (C) study time tracking, (D) goal setting, (E) flexible stats intervals, (F) reading practice mode, (G) sentence practice mode.

---

## Phase 1: Database Migration (database.py)

Add Migration 3 with:

**New tables:**
- `curriculum_state` — per-student curriculum position (current_topik_level, current_position, items_introduced)
- `goals` — student goals (goal_type, target_value, current_value, period, deadline, active)

**ALTER TABLE on practice_log:**
- `duration_seconds INTEGER` — session timing
- `practice_mode TEXT DEFAULT 'speaking'` — speaking/sentence/reading
- `sentence_id INTEGER` — links to sentence used

**New helper functions:**
- `get_curriculum_state()`, `upsert_curriculum_state()`
- `get_sentences_for_items()` — find sentences matching item IDs (for Feature A)

---

## Phase 2: SRS Changes (srs.py)

Rewrite `select_review_items()` with 4-tier priority:
1. **Tier 0 (NEW):** Teacher-assigned unseen items (source IN telegram/signal/manual) — always first
2. **Tier 1:** Overdue SRS items — teacher-assigned boosted to front
3. **Tier 2:** Lowest mastery items (unchanged)
4. **Tier 3 (CHANGED):** Curriculum-ordered unseen items instead of random — ordered by topik_level ASC, id ASC, capped by `new_items_per_session` setting

Add `new_items_per_session` parameter (default 2, configurable per student).

---

## Phase 3: Prompt Generator (prompt_generator.py)

- `generate_prompt_with_sentences()` — tries to find a teacher sentence matching selected items first, falls back to GPT generation
- `format_sentence_prompt()` — formats a specific sentence for sentence-practice mode

---

## Phase 4: Practice Router (practice.py)

Refactor into 3 practice modes:
- **Speaking** (existing, enhanced): uses teacher sentences when available, includes timing
- **Sentence** (new): student speaks a specific teacher-created sentence, gets scored
- **Reading** (new): flashcard-style passive review (Korean → reveal English + examples)

New endpoints:
- `POST /api/practice/reading/complete` — log reading session completion

All modes include `started_at` timestamp for duration tracking.

---

## Phase 5: Correction Service (correction.py)

Accept new params: `duration_seconds`, `practice_mode`, `sentence_id`. Store in practice_log.

---

## Phase 6: Goals Router (NEW: goals.py)

- `GET /api/goals` — list active goals with dynamically calculated progress
- `POST /api/goals` — create goal (types: practice_sessions, new_items, study_time)
- `DELETE /api/goals/{id}` — deactivate goal

Progress calculated dynamically from practice_log/encounters based on period (daily/weekly/custom).

---

## Phase 7: Stats Router (stats.py)

- Add `total_study_seconds` and `study_seconds_7d` to GET /api/stats
- Add `study_seconds` per day to activity endpoint
- Activity and vocab-growth endpoints already accept `days` param — no backend change needed

---

## Phase 8: Settings (settings.py)

Add defaults: `new_items_per_session: "2"`, `curriculum_enabled: "true"`

---

## Phase 9: Main App (main.py)

Register goals router at `/api/goals`.

---

## Phase 10: Frontend — API (api.js)

Add methods: `getGoals()`, `createGoal()`, `deleteGoal()`, `completeReading()`, `startSentencePractice()`

---

## Phase 11: Frontend — Practice Page (practice.js)

- Mode selector: Speaking / Sentence / Reading buttons
- Session timing (capture `started_at`, send with submit)
- Reading mode: flashcard UI (Korean → reveal → next)
- Sentence mode: loads specific sentence, record + submit
- `started_at` included in all session_data submissions

---

## Phase 12: Frontend — Stats Page (stats.js)

- Study time stat card (total + 7d)
- Goals section with progress bars + add goal form
- Interval toggle buttons (7d/30d/90d) on activity and vocab-growth charts

---

## Phase 13: Frontend — Settings Page (settings.js)

Add: "New Items/Session" dropdown, "Curriculum Order" toggle

---

## Phase 14: CSS (style.css)

Minimal additions: mode-btn active state, interval-toggle buttons, flashcard styling.

---

## Implementation Order

1. database.py (migration + helpers)
2. models.py (new schemas)
3. settings.py (new defaults)
4. srs.py (curriculum-aware selection)
5. prompt_generator.py (sentence integration)
6. correction.py (new params)
7. practice.py (3 modes + timing)
8. goals.py + main.py (goals backend)
9. stats.py (study time + intervals)
10. api.js (frontend API)
11. practice.js (mode selector + reading + sentence)
12. stats.js (goals + study time + toggles)
13. settings.js (curriculum settings)
14. style.css (polish)

## File Count
- Modified: 12 files
- New: 1 file (goals.py)

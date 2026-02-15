# Korean Learning App

A comprehensive, data-driven Korean language learning platform with AI-powered speech correction, spaced repetition, structured curriculum, and granular progress tracking.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Analytics & Tracking](#analytics--tracking)
- [Teacher Interface](#teacher-interface)
- [AI Integration](#ai-integration)
- [Self-Hosting Guide](#self-hosting-guide)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)

---

## Overview

This app combines structured curriculum from [HowToStudyKorean.com](https://www.howtostudykorean.com) with AI-powered feedback and sophisticated spaced repetition to create a complete Korean learning platform. It tracks every aspect of student progress—from which items they've been exposed to, which they've actually used, and how often they make mistakes.

### What Makes This Different

- **Objective, granular tracking**: Not just "did they practice" but "did they use each specific grammar point correctly?"
- **AI-powered correction**: GPT-4o analyzes spoken Korean and provides detailed feedback on grammar, vocabulary, and formality
- **Weakness identification**: Automatically identifies items students struggle with (not absorbing, high error rates, stagnation)
- **Structured curriculum**: Browse 30+ lessons from HowToStudyKorean.com with auto-linked vocabulary and grammar
- **Teacher tools**: Telegram/Signal integration for adding content, student progress dashboard

---

## Key Features

### For Students

- **🎤 Speech Practice**: Record responses to situational prompts, get AI feedback
- **📖 Reading Mode**: Flashcard-style passive review with example sentences
- **📚 Structured Lessons**: Browse and practice specific lessons from HowToStudyKorean.com
- **📊 Progress Analytics**: See your TOPIK level, mastery distribution, study time, weakness patterns
- **🎯 Smart SRS**: Modified SM-2 algorithm with weakness weighting
- **📈 Goal Setting**: Set practice goals with deadlines and track progress
- **🔄 Multi-Mode Practice**: Speaking, reading, or sentence repetition

### For Teachers

- **📝 Content Management**: Add vocabulary/grammar via Telegram bot or web interface
- **🔗 Sentence Creation**: Create example sentences with automatic item linking
- **👥 Student Dashboard**: Monitor all students' progress at a glance
- **⚠️ Weakness Reports**: See which items students struggle with
- **📊 Analytics**: Exposure rates, error patterns, mastery by TOPIK level
- **🤖 AI-Assisted**: GPT-4o helps parse natural language item submissions

---

## Architecture

### Tech Stack

**Backend:**
- **FastAPI** (async Python web framework)
- **aiosqlite** (async SQLite database)
- **OpenAI API** (Whisper for transcription, GPT-4o for correction/generation)
- **python-telegram-bot** (Telegram integration)

**Frontend:**
- **Vanilla JavaScript** (SPA with no framework)
- **PWA** (installable, works offline with service worker)
- **Responsive CSS** (mobile-first design)

**Deployment:**
- **systemd** service for auto-start
- **nginx** reverse proxy
- **Docker** (optional, for Signal bot)

### Data Flow

```
┌─────────────┐
│   Student   │
│  (Browser)  │
└──────┬──────┘
       │ Records audio
       ▼
┌─────────────────┐
│   FastAPI App   │
│  ┌───────────┐  │
│  │ Whisper   │  │ ◄─── Transcribe audio
│  │ GPT-4o    │  │ ◄─── Analyze response
│  │ SQLite    │  │ ◄─── Update SRS/mastery
│  └───────────┘  │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│    Teacher      │
│ (Telegram/Web)  │ ◄─── View analytics, add content
└─────────────────┘
```

---

## Database Schema

The app uses a **single SQLite database** (`data/korean_app.db`) with **19 tables** organized into 5 functional areas:

### 1. Core Content (Items & Sentences)

**`items`** - Vocabulary words and grammar patterns
```sql
id, korean, english, item_type (vocab|grammar), topik_level,
source (telegram|signal|manual|seed), tags (JSON array),
pos (part of speech), dictionary_form, grammar_category
```
- 🎯 Purpose: The fundamental units of learning
- 📊 Typical count: 1000-5000 items

**`sentences`** - Example sentences and practice prompts
```sql
id, korean, english, formality (formal|polite|casual),
topik_level, source (teacher|ai_generated), notes
```
- 🎯 Purpose: Contextualized usage examples
- 🔗 Links: `sentence_items` (many-to-many with items)

**`sentence_items`** - Links sentences to their component items
```sql
sentence_id, item_id, UNIQUE(sentence_id, item_id)
```
- 🎯 Purpose: Automatic item detection in sentences

**`examples`** - Additional example sentences per item
```sql
item_id, korean, english, formality
```
- 🎯 Purpose: Multiple usage examples for vocabulary/grammar

### 2. Student Management

**`students`** - Student accounts
```sql
id, username, display_name, password_hash, created_at
```
- 🎯 Purpose: Multi-student support with authentication
- 🔒 Security: bcrypt password hashing

### 3. Learning Progress (SRS & Mastery)

**`srs_state`** - Spaced repetition scheduling (per student, per item)
```sql
item_id, student_id, ease_factor, interval_days,
repetitions, next_review, last_reviewed
```
- 🎯 Purpose: Modified SM-2 algorithm scheduling
- 📈 Controls: When items appear for review

**`mastery`** - Rolling average scores (per student, per item)
```sql
item_id, student_id,
grammar_score, vocab_score, formality_score, overall_score,
practice_count, exposure_count, usage_count, error_count,
last_practiced, updated_at
```
- 🎯 Purpose: Comprehensive performance tracking
- 📊 Key metrics:
  - `exposure_count`: How many times student saw this item (target item in session)
  - `usage_count`: How many times student actually used it in their response
  - `error_count`: How many times they used it incorrectly
  - `overall_score`: Rolling average of performance (0.0-1.0)
  - Sub-scores: Separate tracking for grammar, vocab, formality

**`encounters`** - Event log of every student-item interaction
```sql
student_id, item_id, first_seen, first_practiced,
encounter_count, encounter_type (exposed|used_correctly|used_incorrectly|missing)
```
- 🎯 Purpose: Temporal tracking for trend analysis
- 📈 Enables: "When did they first see this? When did they start using it correctly?"

**`practice_log`** - Complete session history
```sql
item_ids (JSON), prompt, formality, audio_path, transcript,
overall_score, feedback_json, student_id, duration_seconds,
practice_mode (speaking|reading|sentence|lesson), sentence_id, lesson_id
```
- 🎯 Purpose: Audit trail of all practice sessions
- 🔍 Stores: Full GPT feedback, audio files, session metadata

### 4. Curriculum Structure

**`curriculum_units`** - Learning units (e.g., Unit 1, Unit 2)
```sql
unit_number, title, description, topik_level, url, sort_order
```
- 🎯 Purpose: Top-level curriculum organization
- 📚 Current: 2 units from HowToStudyKorean.com

**`curriculum_lessons`** - Individual lessons within units
```sql
unit_id, lesson_number, title, url, description,
sort_order, estimated_hours
```
- 🎯 Purpose: Structured learning path
- 📚 Current: 30 lessons (Lessons 1-30)

**`lesson_items`** - Links lessons to their vocabulary/grammar items
```sql
lesson_id, item_id, is_primary, introduced_order
```
- 🎯 Purpose: Define what each lesson teaches
- 🔗 Auto-matched: Items linked by TOPIK level (can be refined)

**`lesson_progress`** - Student progress through curriculum
```sql
student_id, lesson_id, status (available|in_progress|completed),
started_at, completed_at, mastery_score, practice_count, last_practiced
```
- 🎯 Purpose: Track which lessons student has worked on

**`curriculum_state`** - Student's current position in curriculum
```sql
student_id, current_topik_level, current_position,
items_introduced, updated_at
```
- 🎯 Purpose: Sequential introduction of new items (optional enforcement)

### 5. Analytics & Goals

**`student_level_history`** - TOPIK level over time
```sql
student_id, estimated_level, calculated_at
```
- 🎯 Purpose: Track student progression through TOPIK levels
- 📈 Calculation: Based on mastery of items at each level

**`goals`** - Student-set goals with deadlines
```sql
student_id, goal_type (practice_sessions|new_items|study_time),
target_value, current_value, period (daily|weekly|monthly|custom),
deadline, active, created_at, completed_at
```
- 🎯 Purpose: Motivation and accountability
- 📊 Examples: "Practice 5x this week", "Learn 20 new words by March 1"

**`settings`** - Configuration key-value store
```sql
key, value, student_id (0 = global, >0 = student-specific)
```
- 🎯 Purpose: User preferences, API keys, app config
- 🔧 Examples: `openai_api_key`, `new_items_per_session`, `teacher_password`

---

## Analytics & Tracking

### What Gets Tracked

#### Every Practice Session Captures:

1. **Item Exposure**: Which items were included in the session (target items)
2. **Item Usage**: Which items the student actually used in their response
3. **Item Accuracy**: Which items were used correctly vs. incorrectly
4. **Timing**: Session start, duration, completion
5. **Full Transcript**: Whisper transcription of student's speech
6. **AI Feedback**: Complete GPT-4o analysis (grammar, vocabulary, formality)
7. **Audio Recording**: Saved for review/analysis

#### Key Metrics Per Item (Per Student):

- **Exposure Count**: Times student has been taught this item (it appeared in a practice session)
- **Usage Count**: Times student actually produced this item in their speech
- **Error Count**: Times student used it incorrectly
- **Absorption Rate**: `usage_count / exposure_count` (0.0-1.0)
  - Low = student isn't using what they're taught
- **Error Rate**: `error_count / usage_count` (0.0-1.0)
  - High = student tries but makes mistakes
- **Mastery Score**: Rolling average of performance (0.0-1.0)
  - Calculated from all practice attempts
- **Sub-Scores**: Separate tracking for grammar, vocabulary, formality
- **Last Practiced**: Timestamp of most recent usage

### Analytics Dashboards

#### Student Stats Page

**Overview Cards:**
- Current TOPIK level (estimated from mastery data)
- Items due for review
- Recent practice sessions (7-day)
- Average score (7-day)
- Total study time

**Mastery Distribution:**
- Pie chart: Mastered | Learning | Struggling | Unseen
- Per-TOPIK-level breakdown

**Activity Heatmap:**
- 30-day practice calendar with color intensity
- Shows sessions per day and average score

**Level Progression:**
- TOPIK level over time
- Sparkline of recent progress

**Vocabulary Growth:**
- Cumulative items encountered over time
- New items per week

**⚠️ Items Needing Attention:**
- Auto-identifies problem items sorted by weakness score
- Shows:
  - Absorption rate (using what you're taught?)
  - Error rate (making mistakes when you use it?)
  - Exposure/usage/error counts
  - Weakness type: `not_absorbing` | `high_errors` | `stagnant` | `needs_practice`

**Error Patterns:**
- Error rate by item type (vocab vs. grammar)
- Top 5 most common mistakes
- Error rate by grammar category
- Helps identify systematic weaknesses

#### Teacher Dashboard

**Student Overview:**
- All students at a glance
- Each student's TOPIK level, items due, recent practice, mastery distribution
- Quickly identify who needs help

**Item Management:**
- Browse all vocabulary/grammar
- Filter by TOPIK level, type, source, tags
- See mastery stats across all students
- Edit items, add examples

**Sentence Management:**
- Browse all example sentences
- Create new sentences with auto-item-linking
- See which items are linked
- Filter by formality, TOPIK level

**Practice History:**
- Full audit log of all sessions
- Click to see detailed feedback
- Audio playback
- Identify trends

### How Weakness Tracking Works

#### Automatic Weakness Detection

The system automatically flags items as problematic using these criteria:

**1. Not Absorbing** (`absorption_rate < 0.3` AND `exposure_count > 3`)
- Student has been taught this item repeatedly but rarely uses it
- Example: Exposed 10 times, used 2 times → 20% absorption
- **Action**: Review teaching method, provide more examples, make more salient

**2. High Errors** (`error_rate > 0.5` AND `usage_count > 2`)
- Student attempts to use it but frequently makes mistakes
- Example: Used 10 times, errors 6 times → 60% error rate
- **Action**: Targeted correction, explicit instruction on common mistakes

**3. Stagnant** (`exposure_count >= 5` AND `mastery_score < 0.5`)
- Repeatedly practiced but no improvement
- Example: Exposed 8 times, mastery still 40%
- **Action**: Try different approach, break into smaller components

**4. Needs Practice** (everything else)
- Generally progressing but could use more work

#### Granular Item Tracking Flow

```
Practice Session Starts
  ├─ Target items: A, B, C (exposure_count++ for all)
  │
  ├─ Student speaks: "Korean sentence using items A and D"
  │
  ├─ GPT-4o analyzes:
  │   ├─ Item A: used correctly ✓
  │   ├─ Item B: missing (not used) ✗
  │   ├─ Item C: missing (not used) ✗
  │   └─ Item D: used correctly ✓ (not a target item!)
  │
  └─ Database updates:
      ├─ Item A: usage_count++, mastery += 1.0
      ├─ Item B: error as "missing", mastery += 0.0
      ├─ Item C: error as "missing", mastery += 0.0
      └─ Item D: usage_count++, mastery += 1.0
```

**Key Insight**: The system tracks items the student *actually uses*, not just the ones we asked them to use. This reveals:
- Which items students naturally employ
- Which items they avoid (even when prompted)
- Which items they use unprompted (strong retention)

---

## Teacher Interface

### Adding Content

#### Via Telegram Bot

1. **Send a message** to the bot with vocabulary/grammar
2. **Formats supported**:
   - Natural language: "밥 means rice"
   - Structured: "밥 - rice"
   - GPT fallback: Anything else gets parsed by AI

3. **Automatic processing**:
   - Item type detection (vocab vs. grammar)
   - TOPIK level estimation
   - Deduplication (won't add if already exists)
   - Confirmation with item details

**Example:**
```
Teacher: 먹다 - to eat
Bot: ✅ Added 1 item:
     📗 먹다 → to eat (T1, vocab)
```

#### Via Web Interface

1. Navigate to "관리" (Teacher) tab
2. Click "Add New Item"
3. Fill in form:
   - Korean text
   - English meaning
   - Item type (vocab/grammar)
   - TOPIK level
   - Tags (optional)
   - Grammar category (for grammar items)
   - Dictionary form (for verbs/adjectives)

4. Click "Add Item"

#### Creating Sentences

1. Go to "Sentences" section in teacher tab
2. Click "Add Sentence"
3. Enter Korean sentence
4. (Optional) Enter English translation (auto-translates if omitted)
5. Select formality level
6. **Automatic item linking**: System detects which items appear in the sentence
7. Review linked items, manually add/remove if needed

**Example:**
```
Korean: 저는 어제 친구하고 영화를 봤어요
English: I watched a movie with my friend yesterday

Auto-linked items:
- 저 (I, formal)
- 어제 (yesterday)
- 친구 (friend)
- -하고 (with/and)
- 영화 (movie)
- 보다 (to watch)
- -았/었어요 (past polite ending)
```

### Student Management

#### Creating Students

1. Teacher tab → "Students" section
2. Click "Add Student"
3. Enter username, display name, password
4. Student can now log in with those credentials

#### Monitoring Progress

**Teacher Overview Dashboard** shows for each student:
- Current TOPIK level
- Items due for review
- Recent practice sessions (7-day count)
- Average score
- Mastery distribution
- Items encountered

**Click on a student** to see detailed analytics:
- Full stats page
- Practice history
- Item-by-item mastery
- Weakness reports

### Teaching Suggestions

#### For Best Results:

**1. Regular Content Addition**
- Add 5-10 new items per lesson
- Include both vocabulary and grammar
- Create example sentences for each item
- Tag items by theme (food, daily life, business, etc.)

**2. Monitor Weakness Reports**
- Check "Items Needing Attention" weekly
- Focus on items with:
  - Low absorption (< 30%)
  - High errors (> 50%)
  - Stagnation (no improvement after 5+ exposures)
- **Action**: Create targeted sentences, explain in class, provide mnemonics

**3. Use Sentences Strategically**
- Create sentences using items students struggle with
- Mix difficulty levels (known items + 1-2 new items)
- Vary formality to practice different speech levels
- Link related items in same sentence for context

**4. Track Progress Trends**
- Look at level progression over time
- Celebrate when students move up a TOPIK level
- Identify plateaus and adjust curriculum

**5. Goal Setting**
- Encourage students to set weekly practice goals
- Monitor goal completion rates
- Adjust difficulty based on completion patterns

**6. Curriculum Alignment**
- Use HowToStudyKorean.com lessons as structure
- Students can practice specific lessons
- Track which lessons need more work
- Supplement curriculum with custom sentences

#### Common Patterns to Watch:

**Pattern: High exposure, low usage**
- **Meaning**: Student isn't using what they're taught
- **Causes**: Item not salient, too difficult, not enough context
- **Fix**: Create more example sentences, use in multiple contexts, review in class

**Pattern: High usage, high errors**
- **Meaning**: Student tries but makes mistakes
- **Causes**: Subtle grammar rule, similar forms confused, incomplete understanding
- **Fix**: Explicit instruction on the error pattern, contrastive examples

**Pattern: Uneven mastery across TOPIK levels**
- **Meaning**: Gaps in foundational knowledge
- **Causes**: Skipped lessons, rushed progression
- **Fix**: Review lower-level items, fill gaps before advancing

---

## AI Integration

### OpenAI API Usage

The app uses OpenAI's API for three primary functions:

#### 1. Speech Recognition (Whisper)

- **Model**: `whisper-1`
- **Input**: Student audio recording (WebM/MP3/WAV)
- **Output**: Korean text transcript
- **Accuracy**: Very high for Korean
- **Cost**: ~$0.006 per minute of audio

#### 2. Speech Correction (GPT-4o)

- **Model**: `gpt-4o` (or `gpt-4o-mini` for cost savings)
- **Input**:
  - Target vocabulary/grammar items
  - Expected formality level
  - Practice prompt
  - Student's transcript
- **Output**: Structured JSON with:
  ```json
  {
    "overall_score": 0.85,
    "items_used": [
      {"korean": "먹다", "english": "to eat", "item_type": "vocab",
       "status": "correct", "explanation": "Used correctly in past tense"}
    ],
    "grammar_used": [
      {"pattern": "-았/었어요", "english": "past polite",
       "status": "correct", "explanation": "Proper conjugation"}
    ],
    "formality": {
      "expected": "polite", "detected": "polite", "issues": []
    },
    "corrected_sentence": "Corrected version",
    "natural_alternative": "More natural version",
    "explanation": "Overall feedback in English"
  }
  ```
- **Purpose**: Provides detailed, actionable feedback
- **Cost**: ~$0.01-0.03 per practice session

#### 3. Content Generation (GPT-4o)

**Practice Prompt Generation:**
- Creates situational prompts that require target items
- Example: "You're at a restaurant ordering food. Use 먹다, 주문하다, and -고 싶다"

**Message Parsing:**
- Parses natural language item submissions from teachers
- Example: "kimchi is a Korean fermented vegetable dish" → `{korean: "김치", english: "Korean fermented vegetable dish", type: "vocab"}`

**Translation:**
- Auto-translates Korean sentences to English
- Used when creating sentences without English

**AI-Generated Sentences:**
- Now stored in database with automatic item linking
- Enables tracking exposure to AI-generated content

### API Key Configuration

Set your OpenAI API key in one of two ways:

**1. Environment Variable (for deployment):**
```bash
export OPENAI_API_KEY="sk-..."
```

**2. Database Settings (preferred, allows runtime updates):**
- Teacher tab → Settings
- Add setting: `openai_api_key` = `sk-...`
- Database value takes priority over environment variable

### Cost Estimation

Typical monthly costs (assuming 1 student practicing 5x/week):

- Whisper transcription: ~$1.20/month (20 sessions × 1 min × $0.006)
- GPT-4o correction: ~$4.00/month (20 sessions × $0.02)
- GPT-4o generation: ~$1.00/month (prompts + parsing)

**Total: ~$6-8/student/month**

**Cost Reduction:**
- Use `gpt-4o-mini` for correction/generation (60% cheaper)
- Cache prompts and system messages
- Batch process when possible

---

## Self-Hosting Guide

### Prerequisites

- **OS**: Ubuntu 20.04+ (or any Linux with systemd)
- **Python**: 3.10 or higher
- **Domain** (optional): For HTTPS and production deployment
- **OpenAI API Key**: Required for AI features

### Installation

#### 1. Clone Repository

```bash
cd /home/yourusername
git clone https://github.com/yourusername/korean-app.git
cd korean-app
```

#### 2. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Initialize Database

```bash
# Run migrations
python scripts/run_migrations.py

# Seed initial data (optional, includes sample vocabulary)
python scripts/seed_db.py

# Populate curriculum from HowToStudyKorean.com
python scripts/scrape_curriculum.py
```

#### 4. Configure Environment

Create `.env` file:

```bash
# OpenAI API (required)
OPENAI_API_KEY=sk-your-key-here

# Teacher password for web login
TEACHER_PASSWORD=your-secure-password

# Telegram bot (optional)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ADMIN_CHAT_ID=your-chat-id

# Session secret (generate with: python -c "import secrets; print(secrets.token_hex(32))")
SESSION_SECRET=your-random-secret-key
```

#### 5. Run Development Server

```bash
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload
```

Visit `http://localhost:8100`

### Production Deployment

#### 1. systemd Service

Create `/etc/systemd/system/korean-app.service`:

```ini
[Unit]
Description=Korean Learning App
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/korean-app
Environment="PATH=/home/yourusername/korean-app/venv/bin"
ExecStart=/home/yourusername/korean-app/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8100
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable korean-app
sudo systemctl start korean-app
sudo systemctl status korean-app
```

#### 2. nginx Reverse Proxy

Create `/etc/nginx/sites-available/korean-app`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Larger uploads for audio files
    client_max_body_size 10M;
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/korean-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 3. HTTPS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Optional: Signal Bot Integration

If you want Signal integration for teacher content submission:

1. **Install Docker**:
```bash
sudo apt install docker.io docker-compose
```

2. **Start signal-cli-rest-api**:
```bash
docker-compose up -d
```

3. **Link Signal account** (follow docker logs for QR code)

4. **Configure webhook** in `app/config.py`:
```python
SIGNAL_WEBHOOK_URL = "http://localhost:8101/v2/send"
```

### Backup Strategy

**Critical data to backup**:
- `data/korean_app.db` (entire database)
- `data/audio/` (student recordings)
- `.env` (configuration)

**Backup script** (`scripts/backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="/backups/korean-app"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
sqlite3 data/korean_app.db ".backup '$BACKUP_DIR/korean_app_$DATE.db'"

# Backup audio (if desired)
tar -czf $BACKUP_DIR/audio_$DATE.tar.gz data/audio/

# Keep only last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

**Cron job** (daily backups at 2 AM):
```bash
0 2 * * * /home/yourusername/korean-app/scripts/backup.sh
```

---

## Configuration

### Settings (Database)

Settings can be configured via Teacher interface or directly in the `settings` table:

| Key | Default | Description |
|-----|---------|-------------|
| `openai_api_key` | (none) | OpenAI API key (overrides env var) |
| `new_items_per_session` | `2` | Max new items introduced per practice session |
| `teacher_default_level` | `1` | Default TOPIK level for teacher-added items |
| `teacher_default_tags` | `[]` | Default tags for teacher-added items |

**Student-specific settings** (set `student_id` > 0):
- Same keys as above, but applied per-student
- Example: Student 1 might see 3 new items per session, Student 2 sees 1

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for Whisper/GPT-4o |
| `TEACHER_PASSWORD` | Yes | Password for teacher web login |
| `SESSION_SECRET` | Yes | Secret key for session cookies (generate random) |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for teacher bot |
| `TELEGRAM_ADMIN_CHAT_ID` | No | Telegram chat ID for admin notifications |
| `DATABASE_PATH` | No | Path to SQLite database (default: `data/korean_app.db`) |

---

## Usage

### For Students

1. **Login** with username/password provided by teacher
2. **Practice Tab**:
   - Select formality level (formal/polite/casual)
   - Choose mode (speaking/reading)
   - Click "Start Practice"
   - For speaking: Record your response, tap to stop
   - Get instant AI feedback with corrections
3. **Lessons Tab**:
   - Browse HowToStudyKorean.com curriculum
   - Select a lesson
   - Click "Practice This Lesson" for focused practice
4. **Stats Tab**:
   - View progress, mastery, study time
   - Check "Items Needing Attention"
   - See error patterns
5. **Review Tab**:
   - Browse practice history
   - Review past sessions and feedback
6. **Settings Tab**:
   - Adjust new items per session
   - Set study goals

### For Teachers

1. **Login** with teacher password (선생님 로그인)
2. **관리 (Teacher) Tab**:
   - **Students**: View all students, create new accounts
   - **Items**: Browse/add/edit vocabulary and grammar
   - **Sentences**: Create example sentences with auto-linking
   - **Practice History**: Full audit log of student sessions
3. **Add Content via Telegram**:
   - Message the bot with new items
   - Use `/level 2` to set default TOPIK level
   - Use `/tags food, daily` to set default tags
   - Use `/status` to see current context
4. **Stats Tab**:
   - Monitor all students
   - Identify struggling students
   - Track overall progress

---

## Development

### Project Structure

```
korean_app/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration management
│   ├── database.py             # Database schema & migrations
│   ├── models.py               # Pydantic request/response models
│   ├── auth.py                 # Authentication & sessions
│   ├── routers/                # API endpoints
│   │   ├── practice.py         # Practice sessions
│   │   ├── items.py            # Item CRUD
│   │   ├── sentences.py        # Sentence management
│   │   ├── stats.py            # Analytics endpoints
│   │   ├── curriculum.py       # Lesson browser
│   │   ├── goals.py            # Goal tracking
│   │   └── webhook.py          # Signal webhook
│   ├── services/               # Business logic
│   │   ├── srs.py              # Spaced repetition algorithm
│   │   ├── correction.py       # AI correction pipeline
│   │   ├── prompt_generator.py # AI prompt generation
│   │   ├── openai_service.py   # OpenAI API wrapper
│   │   └── message_parser.py   # Teacher message parsing
│   └── bots/
│       └── telegram_bot.py     # Telegram bot
├── static/                     # Frontend files
│   ├── index.html              # SPA shell
│   ├── css/style.css           # Styling
│   ├── js/
│   │   ├── app.js              # Main app logic
│   │   ├── api.js              # API client
│   │   ├── audio.js            # Audio recording
│   │   ├── components/         # Reusable UI components
│   │   └── pages/              # Page modules (practice, stats, etc.)
│   ├── manifest.json           # PWA manifest
│   └── sw.js                   # Service worker
├── scripts/                    # Utility scripts
│   ├── seed_db.py              # Initial data seeding
│   ├── scrape_curriculum.py   # Curriculum population
│   └── run_migrations.py       # Manual migration runner
├── data/                       # Data directory (gitignored)
│   ├── korean_app.db           # SQLite database
│   └── audio/                  # Recorded audio files
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

### Database Migrations

Migrations are defined in `app/database.py` as a versioned list. When the app starts, it automatically runs any pending migrations.

**Adding a new migration:**

1. Add SQL to `MIGRATIONS` list in `database.py`
2. If migration needs special logic (ALTER TABLE, data transformation), add a runner function:
   ```python
   async def _run_migration_N(db):
       # Migration logic
       pass

   _MIGRATION_RUNNERS = {1: _run_migration_1, N: _run_migration_N}
   ```
3. Restart app (migrations run automatically on startup)

**Current schema version**: Check `schema_version` table

### Adding New Features

**Example: Add a new practice mode**

1. **Update model** (`app/models.py`):
   ```python
   mode: str = "speaking"  # add new mode to comment
   ```

2. **Add handler** (`app/routers/practice.py`):
   ```python
   elif req.mode == "new_mode":
       return await _start_new_mode_practice(db, req, student_id)
   ```

3. **Update frontend** (`static/js/pages/practice.js`):
   ```javascript
   if (this.currentMode === 'new_mode') {
       // Handle new mode
   }
   ```

### Running Tests

Currently no automated tests (TODO). Manual testing checklist:

- [ ] Student login/logout
- [ ] Practice session (speaking mode)
- [ ] Practice session (reading mode)
- [ ] Practice session (lesson mode)
- [ ] AI feedback generation
- [ ] Item CRUD (create, read, update, delete)
- [ ] Sentence creation with auto-linking
- [ ] Teacher dashboard
- [ ] Stats page displays correctly
- [ ] Weakness detection
- [ ] Goal tracking
- [ ] Curriculum browser
- [ ] Telegram bot item submission

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Code Style:**
- Python: Follow PEP 8, use async/await consistently
- JavaScript: Vanilla JS (no framework), modern ES6+ syntax
- SQL: Uppercase keywords, snake_case for columns
- Comments: Explain "why", not "what"

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **HowToStudyKorean.com** - Curriculum structure and lesson organization
- **OpenAI** - Whisper (transcription) and GPT-4o (correction/generation)
- **FastAPI** - High-performance async web framework
- **Anthropic** - Claude Code for development assistance

---

## Roadmap

### Planned Features

- [ ] **Auto-generated flashcards** from practice sessions
- [ ] **Pronunciation scoring** using phonetic analysis
- [ ] **Conversation mode** (multi-turn dialogue practice)
- [ ] **Teacher annotations** on student audio
- [ ] **Collaborative learning** (peer review, leaderboards)
- [ ] **Mobile apps** (React Native for iOS/Android)
- [ ] **Anki integration** (export to Anki decks)
- [ ] **TOPIK test prep** mode
- [ ] **Grammar explanations** (auto-link to HowToStudyKorean.com lessons)
- [ ] **Expansion to Units 3-8** from HowToStudyKorean.com

### Known Issues

- **iOS Safari**: Audio recording requires user interaction before first record
- **Large databases**: Query performance may degrade with >10,000 items (consider indexing)
- **Concurrent access**: SQLite has limited write concurrency (migrate to PostgreSQL for >20 users)

---

## Support

For questions, issues, or feature requests:

- **GitHub Issues**: https://github.com/yourusername/korean-app/issues
- **Email**: your-email@example.com

---

**Built with ❤️ for Korean language learners**

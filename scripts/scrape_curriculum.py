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
        ]
    },
    "Unit 3": {
        "number": 3,
        "title": "Intermediate Korean Grammar",
        "description": "Quoting, causative constructions, complex sentence connectors",
        "topik_level": 3,
        "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/",
        "lessons": [
            {"number": 51, "title": "하기도 하고 ~하기도 하다", "url": "https://www.howtostudykorean.com/unit-3-lessons-51-58/lesson-51/"},
            {"number": 52, "title": "Quoting in Korean (~ㄴ/는다고)", "url": "https://www.howtostudykorean.com/unit-3-lessons-51-58/lesson-52/"},
            {"number": 53, "title": "Quoting Different Endings (~자고, ~냐고)", "url": "https://www.howtostudykorean.com/unit-3-lessons-51-58/lesson-53/"},
            {"number": 54, "title": "Quoted Imperative Sentences: ~(으)라고", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-51-58/lesson-54/"},
            {"number": 55, "title": "Or ~(이)나, ~거나, 아니면", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-51-58/lesson-55/"},
            {"number": 56, "title": "To make, to let: ~게 하다", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-51-58/lesson-56/"},
            {"number": 57, "title": "To make/order: 시키다", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-51-58/lesson-57/"},
            {"number": 58, "title": "I said \"give\": ~아/어 달라고", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-51-58/lesson-58/"},
            {"number": 59, "title": "Difficult words: 어쩌면, 아무래도, 가꾸다, 연세, 뵈다, 차림, 즉", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-59/"},
            {"number": 60, "title": "Difficult words: 차다, 가득, 왠지, 설마, 찍다, 다행, ~달", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-60/"},
            {"number": 61, "title": "To wish/to hope: 바라다, ~기 바랍니다, ~았/었으면 좋겠다", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-61/"},
            {"number": 62, "title": "While: ~(으)면서, ~(으)며", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-62/"},
            {"number": 63, "title": "~ㄹ/을까(요), ~ㄹ/을게요", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-63/"},
            {"number": 64, "title": "Do you think and I am thinking of: ~ㄹ/을까(요)", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-64/"},
            {"number": 65, "title": "I am worried about: ㄹ/을까 봐", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-65/"},
            {"number": 66, "title": "Almost: 거의 and ~ㄹ/을 뻔 했다", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/unit-3-lessons-59-66/lesson-66/"},
            {"number": 67, "title": "Like (~처럼), As if (~듯)", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-67/"},
            {"number": 68, "title": "Only: 유일하다/유일하게", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-68/"},
            {"number": 69, "title": "Nothing but: 밖에 (~ㄹ/을 수밖에 없다)", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-69/"},
            {"number": 70, "title": "Clause Connector: 아/어", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-70/"},
            {"number": 71, "title": "To include (포함하다), to exclude (제외하다)", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-71/"},
            {"number": 72, "title": "As much as: ~만큼, 정도", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-72/"},
            {"number": 73, "title": "Instead (대신에)", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-73/"},
            {"number": 74, "title": "It doesn't matter/Regardless of (상관없다/상관없이)", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-74/"},
            {"number": 75, "title": "I don't care: 신경 안 쓰다", "url": "https://www.howtostudykorean.com/unit-3-intermediate-korean-grammar/lessons-67-75/lesson-75/"},
        ]
    },
    "Unit 4": {
        "number": 4,
        "title": "Upper-Intermediate Korean Grammar",
        "description": "Advanced sentence endings, complex connectors, ~는데 principle",
        "topik_level": 3,
        "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/",
        "lessons": [
            {"number": 76, "title": "~는데 and ~는 데 in Korean", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-76/"},
            {"number": 77, "title": "Continuation of ~는데/~는 데", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-77/"},
            {"number": 78, "title": "~에 의하다 and ~(으)로 인하다", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-78/"},
            {"number": 79, "title": "Difficult words: (그)대로, 인기, 당연하다, 알맞다, 전체", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-79/"},
            {"number": 80, "title": "One should/must not: ~아/어서는 안 되다, ~(으)면 안 되다", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-80/"},
            {"number": 81, "title": "Because (of): ~(으)니까 and ~(으)니", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-81/"},
            {"number": 82, "title": "~구나, ~군 and ~군요", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-82-2/"},
            {"number": 83, "title": "Expressing Surprise or Admiration: ~네(요)", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-76-83/lesson-83/"},
            {"number": 84, "title": "As soon as (~자마자, ~는 대로, ~자)", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-84/"},
            {"number": 85, "title": "To know, to not know (~ㄹ/을/ㄴ/은 줄 알다/모르다), As you know", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-85/"},
            {"number": 86, "title": "Negating Nouns and Clauses (아니라, ~는 게 아니라)", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-86/"},
            {"number": 87, "title": "To decide to do (~기로 하다)", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-87/"},
            {"number": 88, "title": "Many meanings of ~다가", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-88/"},
            {"number": 89, "title": "Comparing using fractions and orders of magnitude", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-89/"},
            {"number": 90, "title": "The meaning of ~잖다 (~잖아, ~잖아요)", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-90/"},
            {"number": 91, "title": "~거든(요): Because, Other meanings", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-84-91/lesson-91/"},
            {"number": 92, "title": "~도록: To an extent, In order to, To make", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-82/"},
            {"number": 93, "title": "~지 and ~죠", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-93/"},
            {"number": 94, "title": "To end up: ~게 되다", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-94/"},
            {"number": 95, "title": "뿐: Just, Only (~ㄹ/을 뿐이다, ~ㄹ/을 뿐만 아니라)", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-95/"},
            {"number": 96, "title": "If one wants to be able to: ~(으)려면", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-96/"},
            {"number": 97, "title": "An abbreviation of 가지다: 갖다", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-97/"},
            {"number": 98, "title": "To pretend to: ~은/ㄴ/는 척하다", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-98/"},
            {"number": 99, "title": "Even if: ~더라도", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-99/"},
            {"number": 100, "title": "The confusing meanings of ~텐데(요)", "url": "https://www.howtostudykorean.com/upper-intermediate-korean-grammar/unit-4-lessons-92-100/lesson-100/"},
        ]
    },
    "Unit 5": {
        "number": 5,
        "title": "Lower-Advanced Korean Grammar",
        "description": "Slang, past perfect, complex grammar patterns with ~더~",
        "topik_level": 4,
        "url": "https://www.howtostudykorean.com/unit-5/",
        "lessons": [
            {"number": 101, "title": "Korean Slang and Abbreviations", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-101/"},
            {"number": 102, "title": "Quoted Abbreviations", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-102/"},
            {"number": 103, "title": "한, 약, ~(으)므로, 전반, 당하다", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-103/"},
            {"number": 104, "title": "~는/은 Adding to More Complicated Things", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-104/"},
            {"number": 105, "title": "Small Grammar Points!", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-105a/"},
            {"number": 106, "title": "Listing Possibilities/Outcomes: ~든지 (간에)", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-106/"},
            {"number": 107, "title": "~도 Revisited", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-107/"},
            {"number": 108, "title": "Past Perfect: ~었~", "url": "https://www.howtostudykorean.com/unit-5/lessons-101-108/lesson-108/"},
            {"number": 109, "title": "~나 보다, ~는/ㄴ가 보다", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-109/"},
            {"number": 110, "title": "어쩔 수 없다", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-110/"},
            {"number": 111, "title": "~(이)라도", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-111/"},
            {"number": 112, "title": "~는 편이다", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-112/"},
            {"number": 113, "title": "On one's way ~는 길", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-113/"},
            {"number": 114, "title": "~는 김에", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-114/"},
            {"number": 115, "title": "I Should Have: ~ㄹ/을걸 (그랬다)", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-115/"},
            {"number": 116, "title": "While in the state of: ~ㄴ/은 채(로)", "url": "https://www.howtostudykorean.com/unit-5/lessons-109-116/lesson-116/"},
            {"number": 117, "title": "~더~ and ~던가", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-117/"},
            {"number": 118, "title": "Stating a fact from experience: ~더라", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-118/"},
            {"number": 119, "title": "~더니 (to notice... then...)", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-119/"},
            {"number": 120, "title": "~다니", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-120/"},
            {"number": 121, "title": "~다 보면", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-121/"},
            {"number": 122, "title": "~다 보니(까)", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-122/"},
            {"number": 123, "title": "~어/어 보니(까)", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-123/"},
            {"number": 124, "title": "To be Worth Doing: ~ㄹ/을 만하다", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-124/"},
            {"number": 125, "title": "~ㄴ/는다니까", "url": "https://www.howtostudykorean.com/unit-5/unit-5-lessons-117-125/lesson-125-i-said-that/"},
        ]
    },
    "Unit 6": {
        "number": 6,
        "title": "Advanced Korean Grammar",
        "description": "Large numbers, specialized particles, advanced sentence connectors",
        "topik_level": 5,
        "url": "https://www.howtostudykorean.com/unit-6/",
        "lessons": [
            {"number": 126, "title": "~별 usage with nouns", "url": "https://www.howtostudykorean.com/lesson-126/"},
            {"number": 127, "title": "~씩 for division and intervals", "url": "https://www.howtostudykorean.com/unit-6/lessons-126-133/lesson-127/"},
            {"number": 128, "title": "~아/어 놓다 and uses of 나다", "url": "https://www.howtostudykorean.com/unit-6/lessons-126-133/lesson-128/"},
            {"number": 129, "title": "넘다 for exceeding thresholds", "url": "https://www.howtostudykorean.com/unit-6/lessons-126-133/lesson-129/"},
            {"number": 130, "title": "Large Korean numbers", "url": "https://www.howtostudykorean.com/unit-6/lessons-126-133/lesson130/"},
            {"number": 131, "title": "사이시옷 (medial ㅅ) rules", "url": "https://www.howtostudykorean.com/unit-6/lessons-126-133/lesson-131/"},
            {"number": 132, "title": "~ㄹ/을수록 grammar attachment", "url": "https://www.howtostudykorean.com/unit-6/lessons-126-133/lesson-132/"},
            {"number": 133, "title": "리 as a descriptive noun", "url": "https://www.howtostudykorean.com/unit-6/lessons-126-133/lesson-133/"},
            {"number": 134, "title": "English-based words (Konglish)", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-134/"},
            {"number": 135, "title": "The syllable 성", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-135/"},
            {"number": 136, "title": "~기에 and ~길래", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-136/"},
            {"number": 137, "title": "~아/어야 usage", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-137/"},
            {"number": 138, "title": "~았/었어야 하다", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-138/"},
            {"number": 139, "title": "~았/었어도 되다", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-139/"},
            {"number": 140, "title": "~(으)로서", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-140/"},
            {"number": 141, "title": "~(으)로써", "url": "https://www.howtostudykorean.com/unit-6/lessons-134-141/lesson-141/"},
            {"number": 142, "title": "Attitude expressions with ~ㄴ/는다니, ~다니, ~(이)라니, ~자니, ~(느)냐니 and ~(으)라니", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-142/"},
            {"number": 143, "title": "Making statements in doubt with ~ㄹ/을걸(요)", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-143/"},
            {"number": 144, "title": "Resignation with ~지 뭐", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-144/"},
            {"number": 145, "title": "Understanding ~란abbreviation", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-145/"},
            {"number": 146, "title": "Causality with ~느라고", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-146/"},
            {"number": 147, "title": "Causality with ~는 바람에", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-147/"},
            {"number": 148, "title": "Habitual action with ~고는 하다 (or ~곤 하다)", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-148/"},
            {"number": 149, "title": "Usage of the adverb 하필", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-149/"},
            {"number": 150, "title": "The adverb 어쩌지and its applications", "url": "https://www.howtostudykorean.com/unit-6/lessons-142-150/lesson-150/"},
        ]
    },
    "Unit 7": {
        "number": 7,
        "title": "Upper-Advanced Korean Grammar",
        "description": "Onomatopoeias, mimetic words, advanced ~(으)려고 and 말/싶다 constructions",
        "topik_level": 6,
        "url": "https://www.howtostudykorean.com/unit-7/",
        "lessons": [
            {"number": 151, "title": "Korean Onomatopoeias", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-151/"},
            {"number": 152, "title": "Mimetic Words", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-152/"},
            {"number": 153, "title": "~려 (Part 1)", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-153/"},
            {"number": 154, "title": "~려 with ~다가", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-154/"},
            {"number": 155, "title": "~(으)려 with ~는 and ~던", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-155/"},
            {"number": 156, "title": "~(으)려 with 참", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-156/"},
            {"number": 157, "title": "Complex Sentence Noun", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-157/"},
            {"number": 158, "title": "위주", "url": "https://www.howtostudykorean.com/unit-7/lessons-151-158/lesson-158/"},
            {"number": 159, "title": "Abbreviations of ~하지 않다: ~치 않다 and ~지 않다", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-159/"},
            {"number": 160, "title": "Complex meanings with ~느냐", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-160/"},
            {"number": 161, "title": "Describing nouns with ~느냐", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-161/"},
            {"number": 162, "title": "Depending on... using ~느냐 with 따르다", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-162/"},
            {"number": 163, "title": "Colloquial sentence endings with 말", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-163/"},
            {"number": 164, "title": "Alternative uses of 말 at sentence end", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-164/"},
            {"number": 165, "title": "Using 말 after ~(으)니 or ~기에", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-165/"},
            {"number": 166, "title": "Emphasis with ~(이)야말로", "url": "https://www.howtostudykorean.com/unit-7/lessons-159-166/lesson-166/"},
            {"number": 167, "title": "Deep-dive into 말다: ~ㄹ/을까 말까 usage", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-167/"},
            {"number": 168, "title": "Applications of 말다 with ~거나", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-168/"},
            {"number": 169, "title": "Applications of 말다 with ~ㄹ/을락 말락", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-169/"},
            {"number": 170, "title": "Using 말다 with ~고 and ~고야", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-170/"},
            {"number": 171, "title": "Extended uses of 싶다 with ~다", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-171/"},
            {"number": 172, "title": "Using 싶다 after ~(으)면", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-172/"},
            {"number": 173, "title": "Additional 싶다 uses after expressions of doubt", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-173/"},
            {"number": 174, "title": "Humble responses to praise/flattery", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-174/"},
            {"number": 175, "title": "Using ~치고 to indicate no exceptions", "url": "https://www.howtostudykorean.com/unit-7/lessons-167-175/lesson-175/"},
        ]
    },
    "Unit 8": {
        "number": 8,
        "title": "Near-Expert Korean Grammar",
        "description": "Nuanced expressions, literary forms, expert-level grammatical patterns",
        "topik_level": 6,
        "url": "https://www.howtostudykorean.com/unit-8/",
        "lessons": [
            {"number": 176, "title": "~아/어 봤자 (Pointlessness/Uselessness)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-176/"},
            {"number": 177, "title": "~오~ (Literary Infix)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-177/"},
            {"number": 178, "title": "~구요 (Particle Alternative)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-178/"},
            {"number": 179, "title": "마련 (Noun as Grammatical Principle)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-179/"},
            {"number": 180, "title": "듯하다 (Inference Expression)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-180/"},
            {"number": 181, "title": "~조차 (Emphatic Particle)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-181/"},
            {"number": 182, "title": "~답다 (Noun-to-Adjective Conversion)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-182/"},
            {"number": 183, "title": "~롭다 (Noun-to-Adjective Conversion)", "url": "https://www.howtostudykorean.com/unit-8/lessons-176-183/lesson-183/"},
            {"number": 184, "title": "~(이)나마 particle usage", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-184/"},
            {"number": 185, "title": "Combining ~ㄴ/은/는데 and ~다가", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-185/"},
            {"number": 186, "title": "Sequential action indication (method 1)", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-186/"},
            {"number": 187, "title": "Sequential action indication (method 2)", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-187/"},
            {"number": 188, "title": "~나 usage with contrasting meaning", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-188/"},
            {"number": 189, "title": "~(으)나 expanded meanings", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-189/"},
            {"number": 190, "title": "하나 마나 construction with ~(으)나", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-190/"},
            {"number": 191, "title": "말다 application for halfhearted actions", "url": "https://www.howtostudykorean.com/unit-8/lessons-184-191/lesson-191/"},
            {"number": 192, "title": "Contraction creating a motherly tone (~ㄴ/는다고 하다)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-192/"},
            {"number": 193, "title": "Soft commands (~(으)렴)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-193/"},
            {"number": 194, "title": "Naming recurring and historical events (counters 회, 차, 제)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-194/"},
            {"number": 195, "title": "Expressive adjective descriptions (~기 그지없다)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-195/"},
            {"number": 196, "title": "Simultaneous actions (pseudo-noun 겸)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-196/"},
            {"number": 197, "title": "Formal pseudo-noun (바)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-197/"},
            {"number": 198, "title": "Situation expressions (~ㄴ/은 셈이다)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-198/"},
            {"number": 199, "title": "Stress particles (~은/는커녕)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-199/"},
            {"number": 200, "title": "Versatile verb (부리다)", "url": "https://www.howtostudykorean.com/unit-8/lessons-192-200/lesson-200/"},
        ]
    },
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

from pydantic import BaseModel
from typing import Optional


class ItemCreate(BaseModel):
    korean: str
    english: str
    item_type: str = "vocab"
    topik_level: int = 1
    source: str = "manual"
    tags: list[str] = []
    notes: str = ""
    pos: Optional[str] = None
    dictionary_form: Optional[str] = None
    grammar_category: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    korean: str
    english: str
    item_type: str
    topik_level: int
    source: str
    tags: list[str]
    notes: str
    pos: Optional[str] = None
    dictionary_form: Optional[str] = None
    grammar_category: Optional[str] = None


class ItemUpdate(BaseModel):
    korean: Optional[str] = None
    english: Optional[str] = None
    item_type: Optional[str] = None
    topik_level: Optional[int] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    pos: Optional[str] = None
    dictionary_form: Optional[str] = None
    grammar_category: Optional[str] = None


class ExampleCreate(BaseModel):
    korean: str
    english: str
    formality: str = "polite"


class PracticeRequest(BaseModel):
    formality: str = "polite"
    topik_level: Optional[int] = None
    item_count: int = 3
    mode: str = "speaking"  # 'speaking', 'sentence', 'reading'
    sentence_id: Optional[int] = None  # for sentence-based practice
    lesson_id: Optional[int] = None  # for lesson-based practice


class PracticePrompt(BaseModel):
    session_id: str
    prompt: str
    prompt_english: str
    formality: str
    item_ids: list[int]
    target_items: list[dict]


class GrammarFeedback(BaseModel):
    point: str
    status: str  # correct, incorrect, missing
    explanation: str


class VocabFeedback(BaseModel):
    word: str
    status: str  # correct, wrong_form, missing
    explanation: str


class FormalityFeedback(BaseModel):
    expected: str
    detected: str
    issues: list[str]


class CorrectionResult(BaseModel):
    overall_score: float
    grammar: list[GrammarFeedback]
    vocabulary: list[VocabFeedback]
    formality: FormalityFeedback
    corrected_sentence: str
    natural_alternative: str
    transcript: str
    explanation: str


class SRSState(BaseModel):
    item_id: int
    ease_factor: float
    interval_days: float
    repetitions: int
    next_review: str


class MasteryInfo(BaseModel):
    item_id: int
    grammar_score: float
    vocab_score: float
    formality_score: float
    overall_score: float
    practice_count: int


class LoginRequest(BaseModel):
    password: str


class StudentLoginRequest(BaseModel):
    username: str
    password: str


class StudentCreate(BaseModel):
    username: str
    display_name: str
    password: str


class SentenceCreate(BaseModel):
    korean: str
    english: str = ""
    formality: str = "polite"
    topik_level: Optional[int] = None  # auto-calculated if not provided
    notes: str = ""


class SettingUpdate(BaseModel):
    value: str


class GoalCreate(BaseModel):
    goal_type: str  # 'practice_sessions', 'new_items', 'study_time'
    target_value: int
    period: str = "weekly"  # 'daily', 'weekly', 'custom'
    deadline: Optional[str] = None  # ISO date, required if period='custom'


class GoalResponse(BaseModel):
    id: int
    goal_type: str
    target_value: int
    current_value: int
    period: str
    deadline: Optional[str]
    created_at: str
    completed_at: Optional[str]
    active: bool
    progress_pct: float


class ReadingPracticeRequest(BaseModel):
    topik_level: Optional[int] = None
    item_count: int = 5

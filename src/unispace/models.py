"""Pydantic-модели предметной области."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def new_id() -> str:
    return uuid4().hex[:12]


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class _Model(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --------------------------------------------------------------------------- материалы


class MaterialCreate(_Model):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=200_000)


class Material(MaterialCreate):
    id: str = Field(default_factory=new_id)
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    word_count: int = 0
    reading_minutes: int = 0
    created_at: dt.datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- AI Tutor


class ChatMessage(_Model):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class TutorRequest(_Model):
    question: str = Field(min_length=1, max_length=4000)
    material_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)


class TutorResponse(_Model):
    answer: str
    model: str
    offline: bool


# --------------------------------------------------------------------------- учебные планы


class SubjectInput(_Model):
    name: str = Field(min_length=1, max_length=100)
    level: int = Field(3, ge=1, le=5, description="Самооценка: 1 — новичок, 5 — отлично знаю")
    exam_date: dt.date | None = None


class PlanRequest(_Model):
    goal: str = Field("", max_length=300)
    subjects: list[SubjectInput] = Field(min_length=1, max_length=20)
    hours_per_week: float = Field(10, gt=0, le=80)
    start_date: dt.date | None = None
    horizon_days: int = Field(14, ge=1, le=90)

    @field_validator("subjects")
    @classmethod
    def _unique_names(cls, value: list[SubjectInput]) -> list[SubjectInput]:
        names = [s.name.casefold() for s in value]
        if len(names) != len(set(names)):
            raise ValueError("Названия предметов должны быть уникальными")
        return value


class StudySession(_Model):
    day: dt.date
    subject: str
    minutes: int
    focus: str


class StudyPlan(_Model):
    id: str = Field(default_factory=new_id)
    goal: str = ""
    start_date: dt.date
    sessions: list[StudySession]
    total_minutes: int
    warnings: list[str] = Field(default_factory=list)
    created_at: dt.datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- тесты


class Question(_Model):
    id: str = Field(default_factory=new_id)
    prompt: str = Field(min_length=1)
    options: list[str] = Field(min_length=2, max_length=6)
    answer_index: int = Field(ge=0)
    explanation: str = ""

    @model_validator(mode="after")
    def _answer_in_range(self) -> Question:
        if self.answer_index >= len(self.options):
            raise ValueError("answer_index выходит за пределы options")
        return self


class Quiz(_Model):
    id: str = Field(default_factory=new_id)
    title: str
    material_id: str | None = None
    questions: list[Question] = Field(min_length=1)
    created_at: dt.datetime = Field(default_factory=utcnow)


class PublicQuestion(_Model):
    """Вопрос без правильного ответа — для показа студенту."""

    id: str
    prompt: str
    options: list[str]


class QuizPublic(_Model):
    id: str
    title: str
    material_id: str | None = None
    questions: list[PublicQuestion]


class QuizGenerateRequest(_Model):
    material_id: str | None = None
    text: str | None = Field(None, max_length=200_000)
    num_questions: int = Field(5, ge=1, le=20)
    title: str | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def _has_source(self) -> QuizGenerateRequest:
        if not self.material_id and not (self.text and self.text.strip()):
            raise ValueError("Укажите material_id или text")
        return self


class QuizSubmission(_Model):
    answers: list[int | None] = Field(max_length=100)
    subject: str | None = Field(
        None, max_length=100, description="Если задан — результат попадёт в успеваемость"
    )


class QuestionResult(_Model):
    question_id: str
    correct: bool
    chosen: int | None
    correct_index: int
    explanation: str = ""


class QuizResult(_Model):
    quiz_id: str
    correct: int
    total: int
    percent: float
    details: list[QuestionResult]


# --------------------------------------------------------------------------- карточки


class FlashcardCreate(_Model):
    deck: str = Field("default", min_length=1, max_length=60)
    front: str = Field(min_length=1, max_length=1000)
    back: str = Field(min_length=1, max_length=2000)


class Flashcard(FlashcardCreate):
    id: str = Field(default_factory=new_id)
    ease: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    due: dt.date = Field(default_factory=dt.date.today)
    last_reviewed: dt.date | None = None
    created_at: dt.datetime = Field(default_factory=utcnow)


class FlashcardGenerateRequest(_Model):
    material_id: str | None = None
    text: str | None = Field(None, max_length=200_000)
    deck: str = Field("default", min_length=1, max_length=60)
    max_cards: int = Field(10, ge=1, le=50)

    @model_validator(mode="after")
    def _has_source(self) -> FlashcardGenerateRequest:
        if not self.material_id and not (self.text and self.text.strip()):
            raise ValueError("Укажите material_id или text")
        return self


class ReviewRequest(_Model):
    grade: int = Field(ge=0, le=5, description="0 — забыл полностью, 5 — вспомнил идеально")


# --------------------------------------------------------------------------- успеваемость


class ProgressCreate(_Model):
    subject: str = Field(min_length=1, max_length=100)
    kind: str = Field("quiz", min_length=1, max_length=40)
    score: float = Field(ge=0)
    max_score: float = Field(100, gt=0)
    recorded_on: dt.date = Field(default_factory=dt.date.today)
    note: str = Field("", max_length=500)

    @model_validator(mode="after")
    def _score_within_max(self) -> ProgressCreate:
        if self.score > self.max_score:
            raise ValueError("score не может превышать max_score")
        return self


class ProgressEntry(ProgressCreate):
    id: str = Field(default_factory=new_id)


class SubjectProgress(_Model):
    subject: str
    entries: int
    average_percent: float
    latest_percent: float
    trend: float = Field(
        description="Изменение среднего процента: недавние результаты минус предыдущие"
    )
    status: Literal["weak", "ok", "strong"]


class ProgressSummary(_Model):
    overall_percent: float | None
    subjects: list[SubjectProgress]
    recommendations: list[str]


# --------------------------------------------------------------------------- дедлайны


class DeadlineCreate(_Model):
    title: str = Field(min_length=1, max_length=200)
    subject: str = Field("", max_length=100)
    due: dt.date
    priority: Priority = Priority.MEDIUM


class Deadline(DeadlineCreate):
    id: str = Field(default_factory=new_id)
    done: bool = False


class DeadlineUpdate(_Model):
    title: str | None = Field(None, min_length=1, max_length=200)
    subject: str | None = Field(None, max_length=100)
    due: dt.date | None = None
    priority: Priority | None = None


class DeadlineView(_Model):
    deadline: Deadline
    days_left: int
    status: Literal["done", "overdue", "today", "soon", "week", "later"]
    urgency: float


# --------------------------------------------------------------------------- сводка


class Dashboard(_Model):
    materials_count: int
    due_flashcards: int
    upcoming_deadlines: list[DeadlineView]
    progress: ProgressSummary

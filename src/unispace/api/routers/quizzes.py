from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...models import (
    ProgressEntry,
    PublicQuestion,
    Quiz,
    QuizGenerateRequest,
    QuizPublic,
    QuizResult,
    QuizSubmission,
)
from ...services.quiz import QuizGenerationError, generate_questions, grade_quiz
from ..deps import Container, get_container

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def _public(quiz: Quiz) -> QuizPublic:
    """Скрывает правильные ответы до сдачи теста."""
    return QuizPublic(
        id=quiz.id,
        title=quiz.title,
        material_id=quiz.material_id,
        questions=[
            PublicQuestion(id=q.id, prompt=q.prompt, options=q.options) for q in quiz.questions
        ],
    )


@router.post("/generate", response_model=QuizPublic, status_code=201)
def generate_quiz(
    payload: QuizGenerateRequest, c: Container = Depends(get_container)
) -> QuizPublic:
    text, material_id, default_title = c.resolve_source(payload.material_id, payload.text, "Тест")
    try:
        questions = generate_questions(text, payload.num_questions, llm=c.llm)
    except QuizGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    quiz = c.store.quizzes.add(
        Quiz(title=payload.title or default_title, material_id=material_id, questions=questions)
    )
    c.persist()
    return _public(quiz)


@router.get("", response_model=list[QuizPublic])
def list_quizzes(c: Container = Depends(get_container)) -> list[QuizPublic]:
    return [_public(q) for q in c.store.quizzes.list()]


@router.get("/{quiz_id}", response_model=QuizPublic)
def get_quiz(quiz_id: str, c: Container = Depends(get_container)) -> QuizPublic:
    return _public(c.store.quizzes.require(quiz_id))


@router.post("/{quiz_id}/submit", response_model=QuizResult)
def submit_quiz(
    quiz_id: str, payload: QuizSubmission, c: Container = Depends(get_container)
) -> QuizResult:
    quiz = c.store.quizzes.require(quiz_id)
    result = grade_quiz(quiz, payload.answers)
    if payload.subject:
        c.store.progress.add(
            ProgressEntry(
                subject=payload.subject,
                kind="quiz",
                score=result.correct,
                max_score=result.total,
                note=f"Тест «{quiz.title}»",
            )
        )
        c.persist()
    return result

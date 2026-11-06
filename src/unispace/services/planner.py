"""Генератор персональных учебных планов.

Каждый учебный день (воскресенье — выходной) бюджет минут делится между предметами.
Вес предмета = (6 − уровень) × срочность, где срочность растёт по мере приближения экзамена.
«Долг» (положенное минус полученное время) не даёт слабо взвешенным предметам выпасть из плана.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..models import PlanRequest, StudyPlan, StudySession, SubjectInput

REST_WEEKDAY = 6  # воскресенье
STUDY_DAYS_PER_WEEK = 6
MAX_SUBJECTS_PER_DAY = 3
MIN_SESSION_MINUTES = 15
STEP_MINUTES = 5

FOCUS_CYCLE = (
    "Изучение теории",
    "Разбор примеров и практика",
    "Самопроверка и тесты",
    "Повторение пройденного",
)


def _round_step(minutes: float) -> int:
    return int(round(minutes / STEP_MINUTES) * STEP_MINUTES)


def _urgency(subject: SubjectInput, day: date) -> float:
    if subject.exam_date is None:
        return 1.0
    days_left = (subject.exam_date - day).days
    return 1.0 + 10.0 / (days_left + 1)


def _focus(subject: SubjectInput, day: date, sessions_done: int) -> str:
    if subject.exam_date is not None:
        days_left = (subject.exam_date - day).days
        if days_left <= 3:
            return "Финальное повторение и пробные тесты"
        if days_left <= 7:
            return "Закрепление и решение задач"
    return FOCUS_CYCLE[sessions_done % len(FOCUS_CYCLE)]


def generate_plan(req: PlanRequest, today: date | None = None) -> StudyPlan:
    start = req.start_date or today or date.today()
    days = [start + timedelta(days=i) for i in range(req.horizon_days)]
    study_days = [d for d in days if d.weekday() != REST_WEEKDAY] or days
    per_day = req.hours_per_week * 60 / STUDY_DAYS_PER_WEEK

    warnings = [
        f"Экзамен по «{s.name}» уже прошёл — предмет исключён из плана."
        for s in req.subjects
        if s.exam_date is not None and s.exam_date < start
    ]

    entitlement = {s.name: 0.0 for s in req.subjects}
    received = dict(entitlement)
    sessions_done = dict.fromkeys(entitlement, 0)
    sessions: list[StudySession] = []

    for day in study_days:
        active = [s for s in req.subjects if s.exam_date is None or s.exam_date >= day]
        if not active:
            break
        weights = {s.name: (6 - s.level) * _urgency(s, day) for s in active}
        total_weight = sum(weights.values())
        for name, weight in weights.items():
            entitlement[name] += per_day * weight / total_weight

        def debt(subject: SubjectInput) -> float:
            return entitlement[subject.name] - received[subject.name]

        ranked = sorted(active, key=lambda s: (-debt(s), s.name))[:MAX_SUBJECTS_PER_DAY]
        shares = {s.name: max(debt(s), 1.0) for s in ranked}
        total_share = sum(shares.values())
        for subject in ranked:
            minutes = max(
                MIN_SESSION_MINUTES, _round_step(per_day * shares[subject.name] / total_share)
            )
            received[subject.name] += minutes
            sessions.append(
                StudySession(
                    day=day,
                    subject=subject.name,
                    minutes=minutes,
                    focus=_focus(subject, day, sessions_done[subject.name]),
                )
            )
            sessions_done[subject.name] += 1

    if not sessions:
        warnings.append("В выбранном периоде нет подходящих учебных дней — план пуст.")

    sessions.sort(key=lambda s: (s.day, -s.minutes, s.subject))
    return StudyPlan(
        goal=req.goal,
        start_date=start,
        sessions=sessions,
        total_minutes=sum(s.minutes for s in sessions),
        warnings=warnings,
    )

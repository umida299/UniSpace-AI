"""Управление дедлайнами: статусы и приоритизация."""

from __future__ import annotations

from datetime import date

from ..models import Deadline, DeadlineView, Priority

PRIORITY_WEIGHT = {Priority.LOW: 1.0, Priority.MEDIUM: 2.0, Priority.HIGH: 3.0}
OVERDUE_BONUS = 10.0


def classify(due: date, today: date) -> str:
    days_left = (due - today).days
    if days_left < 0:
        return "overdue"
    if days_left == 0:
        return "today"
    if days_left <= 3:
        return "soon"
    if days_left <= 7:
        return "week"
    return "later"


def urgency(deadline: Deadline, today: date) -> float:
    """Приоритет × близость срока; просроченные всегда впереди."""
    days_left = (deadline.due - today).days
    score = PRIORITY_WEIGHT[deadline.priority] * (1 + 10 / (max(days_left, 0) + 1))
    if days_left < 0:
        score += OVERDUE_BONUS
    return round(score, 2)


def build_views(
    deadlines: list[Deadline], today: date | None = None, include_done: bool = False
) -> list[DeadlineView]:
    today = today or date.today()
    views = [
        DeadlineView(
            deadline=d,
            days_left=(d.due - today).days,
            status="done" if d.done else classify(d.due, today),  # type: ignore[arg-type]
            urgency=0.0 if d.done else urgency(d, today),
        )
        for d in deadlines
        if include_done or not d.done
    ]
    views.sort(key=lambda v: (v.deadline.done, -v.urgency, v.deadline.due))
    return views

"""Аналитика успеваемости."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from ..models import ProgressEntry, ProgressSummary, SubjectProgress

WEAK_BELOW = 60.0
STRONG_FROM = 85.0
DECLINE_THRESHOLD = -10.0
MAX_WINDOW = 3


def entry_percent(entry: ProgressEntry) -> float:
    return entry.score / entry.max_score * 100


def _trend(percents: list[float]) -> float:
    """Среднее недавних результатов минус среднее предыдущих."""
    n = len(percents)
    if n < 2:
        return 0.0
    k = min(MAX_WINDOW, n // 2)
    recent = percents[n - k :]
    previous = percents[max(0, n - 2 * k) : n - k]
    return round(mean(recent) - mean(previous), 1)


def summarize_progress(entries: list[ProgressEntry]) -> ProgressSummary:
    if not entries:
        return ProgressSummary(
            overall_percent=None,
            subjects=[],
            recommendations=[
                "Добавьте первые результаты тестов и экзаменов, чтобы увидеть аналитику."
            ],
        )

    by_subject: dict[str, list[ProgressEntry]] = defaultdict(list)
    for entry in entries:
        by_subject[entry.subject].append(entry)

    subjects: list[SubjectProgress] = []
    recommendations: list[str] = []
    for name in sorted(by_subject):
        ordered = sorted(by_subject[name], key=lambda e: e.recorded_on)
        percents = [entry_percent(e) for e in ordered]
        average = mean(percents)
        trend = _trend(percents)
        status = "weak" if average < WEAK_BELOW else "strong" if average >= STRONG_FROM else "ok"
        subjects.append(
            SubjectProgress(
                subject=name,
                entries=len(percents),
                average_percent=round(average, 1),
                latest_percent=round(percents[-1], 1),
                trend=trend,
                status=status,
            )
        )
        if status == "weak":
            recommendations.append(
                f"«{name}»: средний результат {average:.0f}% — "
                "запланируйте повторение и пройдите тест."
            )
        if trend <= DECLINE_THRESHOLD:
            recommendations.append(
                f"«{name}»: результаты снижаются ({trend:+.0f} п.п.) — "
                "вернитесь к пройденным темам."
            )

    if not recommendations:
        recommendations.append("Всё идёт хорошо — поддерживайте регулярность занятий.")

    return ProgressSummary(
        overall_percent=round(mean(entry_percent(e) for e in entries), 1),
        subjects=subjects,
        recommendations=recommendations,
    )

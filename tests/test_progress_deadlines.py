from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from unispace.models import Deadline, Priority, ProgressCreate, ProgressEntry
from unispace.services.deadlines import build_views, classify
from unispace.services.progress import summarize_progress

TODAY = date(2026, 11, 6)


def entry(subject, score, day_offset=0, max_score=100):
    return ProgressEntry(
        subject=subject,
        score=score,
        max_score=max_score,
        recorded_on=TODAY + timedelta(days=day_offset),
    )


# ------------------------------------------------------------------ progress


def test_empty_progress():
    summary = summarize_progress([])
    assert summary.overall_percent is None
    assert summary.subjects == [] and summary.recommendations


def test_progress_statuses_and_recommendations():
    summary = summarize_progress(
        [
            entry("Математика", 40),
            entry("Математика", 50, 1),
            entry("История", 90),
            entry("Физика", 70),
        ]
    )
    by_name = {s.subject: s for s in summary.subjects}
    assert by_name["Математика"].status == "weak"
    assert by_name["История"].status == "strong"
    assert by_name["Физика"].status == "ok"
    assert by_name["Математика"].average_percent == 45.0
    assert any("Математика" in r for r in summary.recommendations)
    assert summary.overall_percent == pytest.approx((40 + 50 + 90 + 70) / 4)


def test_progress_trend_positive_and_negative():
    rising = summarize_progress(
        [entry("A", 50, 0), entry("A", 60, 1), entry("A", 80, 2), entry("A", 90, 3)]
    )
    falling = summarize_progress(
        [entry("A", 90, 0), entry("A", 85, 1), entry("A", 60, 2), entry("A", 50, 3)]
    )
    assert rising.subjects[0].trend > 0
    assert falling.subjects[0].trend < 0
    assert any("снижаются" in r for r in falling.recommendations)


def test_progress_single_entry_has_zero_trend():
    assert summarize_progress([entry("A", 70)]).subjects[0].trend == 0.0


def test_progress_uses_max_score():
    summary = summarize_progress([entry("A", 8, max_score=10)])
    assert summary.subjects[0].average_percent == 80.0


def test_progress_validation():
    with pytest.raises(ValidationError):
        ProgressCreate(subject="A", score=11, max_score=10)


# ------------------------------------------------------------------ deadlines


def deadline(title, days, priority=Priority.MEDIUM, done=False):
    return Deadline(title=title, due=TODAY + timedelta(days=days), priority=priority, done=done)


@pytest.mark.parametrize(
    ("days", "status"),
    [
        (-1, "overdue"),
        (0, "today"),
        (1, "soon"),
        (3, "soon"),
        (4, "week"),
        (7, "week"),
        (8, "later"),
    ],
)
def test_classify(days, status):
    assert classify(TODAY + timedelta(days=days), TODAY) == status


def test_overdue_comes_first_then_urgency():
    views = build_views(
        [
            deadline("later-high", 20, Priority.HIGH),
            deadline("tomorrow-low", 1, Priority.LOW),
            deadline("overdue-low", -2, Priority.LOW),
            deadline("tomorrow-high", 1, Priority.HIGH),
        ],
        TODAY,
    )
    assert [v.deadline.title for v in views] == [
        "overdue-low",
        "tomorrow-high",
        "tomorrow-low",
        "later-high",
    ]
    assert views[0].status == "overdue" and views[0].days_left == -2


def test_done_deadlines_hidden_by_default():
    items = [deadline("a", 1), deadline("b", 2, done=True)]
    assert [v.deadline.title for v in build_views(items, TODAY)] == ["a"]
    with_done = build_views(items, TODAY, include_done=True)
    assert [v.deadline.title for v in with_done] == ["a", "b"]
    assert with_done[-1].status == "done"

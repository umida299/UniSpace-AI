from collections import defaultdict
from datetime import date

import pytest
from pydantic import ValidationError

from unispace.models import PlanRequest, SubjectInput
from unispace.services.planner import generate_plan

MONDAY = date(2026, 11, 9)


def make_request(**overrides):
    data = {
        "goal": "Сдать сессию",
        "hours_per_week": 12,
        "start_date": MONDAY,
        "horizon_days": 14,
        "subjects": [
            SubjectInput(name="Математика", level=1, exam_date=date(2026, 11, 19)),
            SubjectInput(name="История", level=4),
        ],
    }
    data.update(overrides)
    return PlanRequest(**data)


def test_no_sessions_on_rest_day():
    plan = generate_plan(make_request())
    assert plan.sessions
    assert all(s.day.weekday() != 6 for s in plan.sessions)


def test_sessions_are_sane():
    plan = generate_plan(make_request())
    assert all(s.minutes >= 15 and s.minutes % 5 == 0 for s in plan.sessions)
    per_day = defaultdict(int)
    for s in plan.sessions:
        per_day[s.day] += s.minutes
    assert max(per_day.values()) <= 150  # бюджет 120 мин/день + округление
    assert plan.total_minutes == sum(s.minutes for s in plan.sessions)


def test_weaker_subject_with_exam_gets_more_time():
    plan = generate_plan(make_request())
    totals = defaultdict(int)
    for s in plan.sessions:
        totals[s.subject] += s.minutes
    assert totals["Математика"] > totals["История"]


def test_no_sessions_after_exam():
    plan = generate_plan(make_request())
    exam = date(2026, 11, 19)
    assert all(s.day <= exam for s in plan.sessions if s.subject == "Математика")


def test_exam_week_focus_is_intensive():
    plan = generate_plan(make_request())
    last = [s for s in plan.sessions if s.subject == "Математика" and s.day == date(2026, 11, 18)]
    assert last and "Финальное повторение" in last[0].focus


def test_every_subject_appears():
    plan = generate_plan(make_request())
    assert {s.subject for s in plan.sessions} == {"Математика", "История"}


def test_past_exam_is_excluded_with_warning():
    req = make_request(
        subjects=[
            SubjectInput(name="Физика", level=3, exam_date=date(2026, 11, 1)),
            SubjectInput(name="Химия", level=3),
        ]
    )
    plan = generate_plan(req)
    assert any("Физика" in w for w in plan.warnings)
    assert {s.subject for s in plan.sessions} == {"Химия"}


def test_all_exams_past_gives_empty_plan_with_warning():
    req = make_request(subjects=[SubjectInput(name="Физика", exam_date=date(2026, 11, 1))])
    plan = generate_plan(req)
    assert plan.sessions == []
    assert plan.total_minutes == 0
    assert plan.warnings


def test_duplicate_subject_names_rejected():
    with pytest.raises(ValidationError):
        make_request(subjects=[SubjectInput(name="Физика"), SubjectInput(name="физика")])


def test_plan_is_deterministic():
    first = generate_plan(make_request())
    second = generate_plan(make_request())
    assert [(s.day, s.subject, s.minutes, s.focus) for s in first.sessions] == [
        (s.day, s.subject, s.minutes, s.focus) for s in second.sessions
    ]

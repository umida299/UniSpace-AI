"""Сквозные тесты API. Пропускаются, если не установлены fastapi/httpx."""

import pytest
from samples import SAMPLE_TEXT

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from unispace.ai.llm import OfflineLLM  # noqa: E402
from unispace.ai.tutor import Tutor  # noqa: E402
from unispace.api.app import create_app  # noqa: E402
from unispace.api.deps import Container  # noqa: E402
from unispace.config import Settings  # noqa: E402
from unispace.storage import Store  # noqa: E402

API = "/api/v1"


@pytest.fixture
def client(tmp_path):
    llm = OfflineLLM()
    container = Container(
        store=Store(), llm=llm, tutor=Tutor(llm), data_file=tmp_path / "data.json"
    )
    return TestClient(create_app(Settings(), container=container))


def make_material(client):
    response = client.post(f"{API}/materials", json={"title": "Биология", "text": SAMPLE_TEXT})
    assert response.status_code == 201
    return response.json()


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["offline"] is True


def test_material_crud(client):
    material = make_material(client)
    assert material["keywords"] and material["summary"]
    assert client.get(f"{API}/materials/{material['id']}").status_code == 200
    assert len(client.get(f"{API}/materials").json()) == 1
    assert client.delete(f"{API}/materials/{material['id']}").status_code == 204
    assert client.get(f"{API}/materials/{material['id']}").status_code == 404


def test_validation_error(client):
    assert client.post(f"{API}/materials", json={"title": "", "text": "x"}).status_code == 422


def test_quiz_flow_hides_answers_and_records_progress(client):
    material = make_material(client)
    quiz = client.post(
        f"{API}/quizzes/generate", json={"material_id": material["id"], "num_questions": 3}
    ).json()
    assert quiz["questions"]
    assert all("answer_index" not in q for q in quiz["questions"])

    result = client.post(
        f"{API}/quizzes/{quiz['id']}/submit",
        json={"answers": [0] * len(quiz["questions"]), "subject": "Биология"},
    ).json()
    assert result["total"] == len(quiz["questions"])

    summary = client.get(f"{API}/progress/summary").json()
    assert summary["subjects"][0]["subject"] == "Биология"


def test_quiz_from_too_short_text_is_422(client):
    response = client.post(f"{API}/quizzes/generate", json={"text": "Коротко."})
    assert response.status_code == 422


def test_quiz_requires_source(client):
    assert client.post(f"{API}/quizzes/generate", json={}).status_code == 422


def test_flashcard_review_cycle(client):
    material = make_material(client)
    cards = client.post(
        f"{API}/flashcards/generate", json={"material_id": material["id"], "deck": "bio"}
    ).json()
    assert cards
    due = client.get(f"{API}/flashcards/due", params={"deck": "bio"}).json()
    assert len(due) == len(cards)

    reviewed = client.post(f"{API}/flashcards/{cards[0]['id']}/review", json={"grade": 5}).json()
    assert reviewed["repetitions"] == 1
    due_after = client.get(f"{API}/flashcards/due").json()
    assert len(due_after) == len(cards) - 1
    assert (
        client.post(f"{API}/flashcards/{cards[0]['id']}/review", json={"grade": 9}).status_code
        == 422
    )


def test_plan(client):
    response = client.post(
        f"{API}/plans",
        json={
            "hours_per_week": 10,
            "subjects": [{"name": "Математика", "level": 2}, {"name": "История", "level": 4}],
        },
    )
    assert response.status_code == 201
    assert response.json()["sessions"]


def test_deadlines(client):
    created = client.post(
        f"{API}/deadlines", json={"title": "Курсовая", "due": "2020-01-01", "priority": "high"}
    ).json()
    listed = client.get(f"{API}/deadlines").json()
    assert listed[0]["status"] == "overdue"

    patched = client.patch(f"{API}/deadlines/{created['id']}", json={"title": "Курсовая v2"}).json()
    assert patched["title"] == "Курсовая v2" and patched["priority"] == "high"

    client.post(f"{API}/deadlines/{created['id']}/complete")
    assert client.get(f"{API}/deadlines").json() == []
    assert len(client.get(f"{API}/deadlines", params={"include_done": True}).json()) == 1


def test_tutor_offline(client):
    material = make_material(client)
    body = client.post(
        f"{API}/tutor/ask", json={"question": "Что такое хлорофилл?", "material_id": material["id"]}
    ).json()
    assert body["offline"] is True and body["answer"]
    assert (
        client.post(f"{API}/tutor/ask", json={"question": "?", "material_id": "nope"}).status_code
        == 404
    )


def test_dashboard_and_persistence(client, tmp_path):
    make_material(client)
    client.post(f"{API}/deadlines", json={"title": "Экзамен", "due": "2030-01-01"})
    dashboard = client.get(f"{API}/dashboard").json()
    assert dashboard["materials_count"] == 1
    assert len(dashboard["upcoming_deadlines"]) == 1
    assert (tmp_path / "data.json").exists()

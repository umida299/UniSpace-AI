from datetime import date, timedelta

import pytest
from samples import SAMPLE_TEXT

from unispace.models import Flashcard
from unispace.services.flashcards import MIN_EASE, due_cards, generate_cards, review_card

TODAY = date(2026, 11, 6)


def card(**kw):
    return Flashcard(deck="bio", front="Q", back="A", due=TODAY, **kw)


def test_first_reviews_follow_sm2_intervals():
    c = review_card(card(), 5, TODAY)
    assert (c.repetitions, c.interval_days, c.due) == (1, 1, TODAY + timedelta(days=1))
    c = review_card(c, 5, TODAY)
    assert (c.repetitions, c.interval_days) == (2, 6)
    c = review_card(c, 5, TODAY)
    assert c.repetitions == 3 and c.interval_days > 6
    assert c.last_reviewed == TODAY


def test_failed_review_resets_progress():
    c = review_card(review_card(card(), 5, TODAY), 5, TODAY)
    c = review_card(c, 2, TODAY)
    assert (c.repetitions, c.interval_days) == (0, 1)


def test_ease_has_floor():
    c = card()
    for _ in range(20):
        c = review_card(c, 0, TODAY)
    assert c.ease == MIN_EASE


def test_perfect_reviews_raise_ease():
    assert review_card(card(), 5, TODAY).ease > 2.5


def test_review_does_not_mutate_original():
    original = card()
    review_card(original, 5, TODAY)
    assert original.repetitions == 0


@pytest.mark.parametrize("grade", [-1, 6])
def test_invalid_grade(grade):
    with pytest.raises(ValueError):
        review_card(card(), grade, TODAY)


def test_due_cards_filtering():
    due = card()
    future = Flashcard(deck="bio", front="F", back="B", due=TODAY + timedelta(days=3))
    other_deck = Flashcard(deck="math", front="M", back="B", due=TODAY)
    cards = [future, due, other_deck]
    assert due_cards(cards, TODAY) == [due, other_deck] or due_cards(cards, TODAY) == [
        other_deck,
        due,
    ]
    assert due_cards(cards, TODAY, deck="bio") == [due]
    assert len(due_cards(cards, TODAY, limit=1)) == 1
    assert due_cards(cards, TODAY + timedelta(days=3), deck="bio") == [due, future]


def test_generate_cards_extracts_definition_first():
    cards = generate_cards(SAMPLE_TEXT, deck="bio", max_cards=5)
    assert cards[0].front == "Что такое Фотосинтез?"
    assert cards[0].back.startswith("процесс преобразования")
    assert not cards[0].back.endswith(".")
    assert all(c.deck == "bio" for c in cards)
    assert len(cards) <= 5
    assert len({c.front for c in cards}) == len(cards)


def test_generate_cards_english_definition():
    cards = generate_cards(
        "Mitochondria are organelles that produce most of the cell's energy.", max_cards=3
    )
    assert cards[0].front == "Define: Mitochondria"


def test_generate_cards_from_nothing():
    assert generate_cards("ok") == []

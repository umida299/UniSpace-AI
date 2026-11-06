"""Умные карточки: интервальные повторения SM-2 и генерация из текста."""

from __future__ import annotations

import re
from datetime import date, timedelta

from ..models import Flashcard
from .quiz import QuizGenerationError, generate_cloze_questions
from .text import split_sentences

MIN_EASE = 1.3
MAX_TERM_WORDS = 6

_DEF_RU = re.compile(r"^(?P<term>[^,:;()]{2,60}?)\s+[—–-]\s+(?:это\s+)?(?P<definition>.{10,})$")
_DEF_EN = re.compile(
    r"^(?P<term>[A-Z][^,:;()]{1,50}?)\s+(?:is|are|refers to|means)\s+(?P<definition>.{10,})$"
)


def review_card(card: Flashcard, grade: int, today: date | None = None) -> Flashcard:
    """Алгоритм SM-2. grade: 0 — забыл полностью … 5 — вспомнил идеально."""
    if not 0 <= grade <= 5:
        raise ValueError("grade должен быть в диапазоне 0–5")
    today = today or date.today()
    ease = max(MIN_EASE, card.ease + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))

    if grade < 3:
        repetitions, interval = 0, 1
    else:
        repetitions = card.repetitions + 1
        if card.repetitions == 0:
            interval = 1
        elif card.repetitions == 1:
            interval = 6
        else:
            interval = max(1, round(card.interval_days * ease))

    return card.model_copy(
        update={
            "ease": round(ease, 2),
            "interval_days": interval,
            "repetitions": repetitions,
            "due": today + timedelta(days=interval),
            "last_reviewed": today,
        }
    )


def due_cards(
    cards: list[Flashcard],
    today: date | None = None,
    deck: str | None = None,
    limit: int | None = None,
) -> list[Flashcard]:
    today = today or date.today()
    selected = [c for c in cards if c.due <= today and (deck is None or c.deck == deck)]
    selected.sort(key=lambda c: (c.due, c.created_at))
    return selected[:limit] if limit else selected


def _definition_card(sentence: str, deck: str) -> Flashcard | None:
    sentence = sentence.strip()
    match = _DEF_RU.match(sentence)
    front_template = "Что такое {term}?"
    if match is None:
        match = _DEF_EN.match(sentence)
        front_template = "Define: {term}"
    if match is None:
        return None
    term = match.group("term").strip()
    if len(term.split()) > MAX_TERM_WORDS:
        return None
    definition = match.group("definition").strip().rstrip(".")
    return Flashcard(deck=deck, front=front_template.format(term=term), back=definition)


def generate_cards(text: str, deck: str = "default", max_cards: int = 10) -> list[Flashcard]:
    """Карточки «термин → определение» из предложений-определений, затем cloze-карточки."""
    cards: list[Flashcard] = []
    seen: set[str] = set()

    for sentence in split_sentences(text):
        if len(cards) >= max_cards:
            break
        card = _definition_card(sentence, deck)
        if card and card.front.casefold() not in seen:
            seen.add(card.front.casefold())
            cards.append(card)

    remaining = max_cards - len(cards)
    if remaining > 0:
        try:
            questions = generate_cloze_questions(text, n=remaining, seed=0)
        except QuizGenerationError:
            questions = []
        for question in questions:
            if question.prompt.casefold() not in seen:
                seen.add(question.prompt.casefold())
                cards.append(
                    Flashcard(
                        deck=deck,
                        front=question.prompt,
                        back=question.options[question.answer_index],
                    )
                )
    return cards[:max_cards]

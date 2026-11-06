from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ...models import (
    Flashcard,
    FlashcardCreate,
    FlashcardGenerateRequest,
    ReviewRequest,
)
from ...services.flashcards import due_cards, generate_cards, review_card
from ..deps import Container, get_container

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.post("", response_model=Flashcard, status_code=201)
def create_card(payload: FlashcardCreate, c: Container = Depends(get_container)) -> Flashcard:
    card = c.store.flashcards.add(Flashcard(**payload.model_dump()))
    c.persist()
    return card


@router.post("/generate", response_model=list[Flashcard], status_code=201)
def generate(
    payload: FlashcardGenerateRequest, c: Container = Depends(get_container)
) -> list[Flashcard]:
    text, _, _ = c.resolve_source(payload.material_id, payload.text, "")
    cards = generate_cards(text, deck=payload.deck, max_cards=payload.max_cards)
    if not cards:
        raise HTTPException(status_code=422, detail="Не удалось выделить карточки из текста")
    for card in cards:
        c.store.flashcards.add(card)
    c.persist()
    return cards


@router.get("", response_model=list[Flashcard])
def list_cards(deck: str | None = None, c: Container = Depends(get_container)) -> list[Flashcard]:
    return [card for card in c.store.flashcards.list() if deck is None or card.deck == deck]


@router.get("/due", response_model=list[Flashcard])
def list_due(
    deck: str | None = None,
    limit: int | None = Query(None, ge=1, le=200),
    c: Container = Depends(get_container),
) -> list[Flashcard]:
    return due_cards(c.store.flashcards.list(), deck=deck, limit=limit)


@router.post("/{card_id}/review", response_model=Flashcard)
def review(
    card_id: str, payload: ReviewRequest, c: Container = Depends(get_container)
) -> Flashcard:
    card = c.store.flashcards.require(card_id)
    updated = c.store.flashcards.replace(review_card(card, payload.grade))
    c.persist()
    return updated


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: str, c: Container = Depends(get_container)) -> Response:
    c.store.flashcards.delete(card_id)
    c.persist()
    return Response(status_code=204)

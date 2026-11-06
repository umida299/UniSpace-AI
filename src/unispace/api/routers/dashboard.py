from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from ...models import Dashboard
from ...services.deadlines import build_views
from ...services.flashcards import due_cards
from ...services.progress import summarize_progress
from ..deps import Container, get_container

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

UPCOMING_LIMIT = 5


@router.get("", response_model=Dashboard)
def get_dashboard(c: Container = Depends(get_container)) -> Dashboard:
    today = date.today()  # по часовому поясу сервера
    return Dashboard(
        materials_count=c.store.materials.count(),
        due_flashcards=len(due_cards(c.store.flashcards.list(), today)),
        upcoming_deadlines=build_views(c.store.deadlines.list(), today)[:UPCOMING_LIMIT],
        progress=summarize_progress(c.store.progress.list()),
    )

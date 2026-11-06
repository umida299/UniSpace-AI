from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ...models import ProgressCreate, ProgressEntry, ProgressSummary
from ...services.progress import summarize_progress
from ..deps import Container, get_container

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("", response_model=ProgressEntry, status_code=201)
def add_entry(payload: ProgressCreate, c: Container = Depends(get_container)) -> ProgressEntry:
    entry = c.store.progress.add(ProgressEntry(**payload.model_dump()))
    c.persist()
    return entry


@router.get("", response_model=list[ProgressEntry])
def list_entries(
    subject: str | None = None, c: Container = Depends(get_container)
) -> list[ProgressEntry]:
    return [e for e in c.store.progress.list() if subject is None or e.subject == subject]


@router.get("/summary", response_model=ProgressSummary)
def summary(c: Container = Depends(get_container)) -> ProgressSummary:
    return summarize_progress(c.store.progress.list())


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: str, c: Container = Depends(get_container)) -> Response:
    c.store.progress.delete(entry_id)
    c.persist()
    return Response(status_code=204)

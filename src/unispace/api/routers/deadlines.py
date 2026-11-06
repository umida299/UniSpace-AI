from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ...models import Deadline, DeadlineCreate, DeadlineUpdate, DeadlineView
from ...services.deadlines import build_views
from ..deps import Container, get_container

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.post("", response_model=Deadline, status_code=201)
def create_deadline(payload: DeadlineCreate, c: Container = Depends(get_container)) -> Deadline:
    deadline = c.store.deadlines.add(Deadline(**payload.model_dump()))
    c.persist()
    return deadline


@router.get("", response_model=list[DeadlineView])
def list_deadlines(
    include_done: bool = False, c: Container = Depends(get_container)
) -> list[DeadlineView]:
    return build_views(c.store.deadlines.list(), include_done=include_done)


@router.patch("/{deadline_id}", response_model=Deadline)
def update_deadline(
    deadline_id: str, payload: DeadlineUpdate, c: Container = Depends(get_container)
) -> Deadline:
    deadline = c.store.deadlines.require(deadline_id)
    updated = deadline.model_copy(update=payload.model_dump(exclude_unset=True))
    c.store.deadlines.replace(updated)
    c.persist()
    return updated


@router.post("/{deadline_id}/complete", response_model=Deadline)
def complete_deadline(deadline_id: str, c: Container = Depends(get_container)) -> Deadline:
    deadline = c.store.deadlines.require(deadline_id)
    updated = c.store.deadlines.replace(deadline.model_copy(update={"done": True}))
    c.persist()
    return updated


@router.delete("/{deadline_id}", status_code=204)
def delete_deadline(deadline_id: str, c: Container = Depends(get_container)) -> Response:
    c.store.deadlines.delete(deadline_id)
    c.persist()
    return Response(status_code=204)

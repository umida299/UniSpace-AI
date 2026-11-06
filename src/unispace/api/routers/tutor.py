from __future__ import annotations

from fastapi import APIRouter, Depends

from ...models import TutorRequest, TutorResponse
from ..deps import Container, get_container

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/ask", response_model=TutorResponse)
def ask_tutor(payload: TutorRequest, c: Container = Depends(get_container)) -> TutorResponse:
    context, _, _ = c.resolve_source(payload.material_id, None, "")
    return c.tutor.ask(payload.question, context=context or None, history=payload.history)

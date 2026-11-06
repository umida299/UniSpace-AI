from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ...models import PlanRequest, StudyPlan
from ...services.planner import generate_plan
from ..deps import Container, get_container

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=StudyPlan, status_code=201)
def create_plan(payload: PlanRequest, c: Container = Depends(get_container)) -> StudyPlan:
    plan = c.store.plans.add(generate_plan(payload))
    c.persist()
    return plan


@router.get("", response_model=list[StudyPlan])
def list_plans(c: Container = Depends(get_container)) -> list[StudyPlan]:
    return c.store.plans.list()


@router.get("/{plan_id}", response_model=StudyPlan)
def get_plan(plan_id: str, c: Container = Depends(get_container)) -> StudyPlan:
    return c.store.plans.require(plan_id)


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: str, c: Container = Depends(get_container)) -> Response:
    c.store.plans.delete(plan_id)
    c.persist()
    return Response(status_code=204)

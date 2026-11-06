from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ...models import Material, MaterialCreate
from ...services.materials import analyze_material
from ..deps import Container, get_container

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("", response_model=Material, status_code=201)
def create_material(payload: MaterialCreate, c: Container = Depends(get_container)) -> Material:
    material = c.store.materials.add(analyze_material(payload.title, payload.text))
    c.persist()
    return material


@router.get("", response_model=list[Material])
def list_materials(c: Container = Depends(get_container)) -> list[Material]:
    return c.store.materials.list()


@router.get("/{material_id}", response_model=Material)
def get_material(material_id: str, c: Container = Depends(get_container)) -> Material:
    return c.store.materials.require(material_id)


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: str, c: Container = Depends(get_container)) -> Response:
    c.store.materials.delete(material_id)
    c.persist()
    return Response(status_code=204)

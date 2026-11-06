"""Контейнер зависимостей приложения."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from ..ai.llm import LLMClient
from ..ai.tutor import Tutor
from ..storage import Store


@dataclass
class Container:
    store: Store
    llm: LLMClient
    tutor: Tutor
    data_file: Path | None = None

    def persist(self) -> None:
        """Сохраняет данные на диск, если задан UNISPACE_DATA_FILE."""
        if self.data_file is not None:
            self.store.save(self.data_file)

    def resolve_source(
        self, material_id: str | None, text: str | None, default_title: str
    ) -> tuple[str, str | None, str]:
        """Возвращает (текст, id материала, заголовок) из материала или из переданного текста."""
        if material_id:
            material = self.store.materials.require(material_id)
            return material.text, material.id, material.title
        return (text or "").strip(), None, default_title


def get_container(request: Request) -> Container:
    return request.app.state.container

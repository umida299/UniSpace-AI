"""Простое хранилище: коллекции в памяти с сохранением в JSON-файл.

Подходит для прототипа и локального запуска. Для продакшена замените на БД
(см. docs/ROADMAP.md).
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .models import Deadline, Flashcard, Material, ProgressEntry, Quiz, StudyPlan

T = TypeVar("T", bound=BaseModel)


class NotFoundError(LookupError):
    """Запись с таким id не найдена."""


class Collection(Generic[T]):
    def __init__(self, label: str, model: type[T]) -> None:
        self.label = label
        self.model = model
        self._items: dict[str, T] = {}

    def add(self, item: T) -> T:
        self._items[item.id] = item  # type: ignore[attr-defined]
        return item

    def get(self, item_id: str) -> T | None:
        return self._items.get(item_id)

    def require(self, item_id: str) -> T:
        item = self._items.get(item_id)
        if item is None:
            raise NotFoundError(f"{self.label} '{item_id}' не найден")
        return item

    def replace(self, item: T) -> T:
        self.require(item.id)  # type: ignore[attr-defined]
        return self.add(item)

    def delete(self, item_id: str) -> None:
        if self._items.pop(item_id, None) is None:
            raise NotFoundError(f"{self.label} '{item_id}' не найден")

    def list(self) -> list[T]:
        return list(self._items.values())

    def count(self) -> int:
        return len(self._items)

    def dump(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.list()]

    def load(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.add(self.model.model_validate(row))


class Store:
    def __init__(self) -> None:
        self.materials: Collection[Material] = Collection("Материал", Material)
        self.plans: Collection[StudyPlan] = Collection("План", StudyPlan)
        self.quizzes: Collection[Quiz] = Collection("Тест", Quiz)
        self.flashcards: Collection[Flashcard] = Collection("Карточка", Flashcard)
        self.progress: Collection[ProgressEntry] = Collection("Запись успеваемости", ProgressEntry)
        self.deadlines: Collection[Deadline] = Collection("Дедлайн", Deadline)
        self._lock = threading.RLock()

    def _collections(self) -> dict[str, Collection[Any]]:
        return {
            "materials": self.materials,
            "plans": self.plans,
            "quizzes": self.quizzes,
            "flashcards": self.flashcards,
            "progress": self.progress,
            "deadlines": self.deadlines,
        }

    def save(self, path: Path) -> None:
        """Атомарно записывает все коллекции в JSON."""
        with self._lock:
            data = {name: col.dump() for name, col in self._collections().items()}
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, path)

    @classmethod
    def load(cls, path: Path) -> Store:
        store = cls()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for name, col in store._collections().items():
                col.load(data.get(name, []))
        return store

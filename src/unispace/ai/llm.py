"""Абстракция над языковой моделью: Claude через SDK или офлайн-заглушка."""

from __future__ import annotations

import logging
from typing import Protocol

from ..config import Settings

logger = logging.getLogger(__name__)

Messages = list[dict[str, str]]


class LLMError(RuntimeError):
    """Ошибка обращения к языковой модели."""


class LLMClient(Protocol):
    name: str
    offline: bool

    def complete(self, system: str, messages: Messages, max_tokens: int = 1024) -> str: ...


class OfflineLLM:
    """Работает без сети: возвращает наводящие вопросы вместо объяснения."""

    name = "offline"
    offline = True

    def complete(self, system: str, messages: Messages, max_tokens: int = 1024) -> str:
        question = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        snippet = question.strip().replace("\n", " ")[:120]
        return (
            "AI Tutor работает в офлайн-режиме (не задан ANTHROPIC_API_KEY), "
            "поэтому полноценного объяснения я дать не могу. Давайте разберём вопрос по шагам:\n"
            f"1. Своими словами: что именно в вопросе «{snippet}» вам непонятно?\n"
            "2. Какие связанные понятия вы уже знаете?\n"
            "3. Запишите первый шаг решения и сверьтесь с конспектом.\n"
            "Чтобы получать развёрнутые объяснения, задайте ANTHROPIC_API_KEY."
        )


class AnthropicLLM:
    offline = False

    def __init__(self, api_key: str, model: str) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "Пакет 'anthropic' не установлен: pip install 'unispace-ai[ai]'"
            ) from exc
        self.name = model
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, system: str, messages: Messages, max_tokens: int = 1024) -> str:
        try:
            response = self._client.messages.create(
                model=self._model, max_tokens=max_tokens, system=system, messages=messages
            )
        except Exception as exc:  # SDK бросает собственную иерархию исключений
            raise LLMError(f"Ошибка обращения к модели: {exc}") from exc
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        if not text.strip():
            raise LLMError("Модель вернула пустой ответ")
        return text


def build_llm(settings: Settings) -> LLMClient:
    """Claude, если есть ключ и SDK; иначе офлайн-режим."""
    if settings.anthropic_api_key:
        try:
            return AnthropicLLM(settings.anthropic_api_key, settings.model)
        except LLMError as exc:
            logger.warning("%s — переключаюсь на офлайн-режим", exc)
    return OfflineLLM()

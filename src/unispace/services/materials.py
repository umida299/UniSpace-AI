"""Анализ учебных материалов."""

from __future__ import annotations

import math

from ..models import Material
from .text import extract_keywords, summarize, tokenize

WORDS_PER_MINUTE = 180


def analyze_material(title: str, text: str) -> Material:
    words = len(tokenize(text))
    return Material(
        title=title,
        text=text,
        summary=summarize(text),
        keywords=extract_keywords(text, top_n=10),
        word_count=words,
        reading_minutes=max(1, math.ceil(words / WORDS_PER_MINUTE)) if words else 0,
    )

"""Лёгкая обработка текста без внешних зависимостей (ru/en).

Морфологии нет: русские словоформы считаются разными словами.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\-]*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+|\n+")

STOPWORDS = frozenset(
    """
    что как это так его все она они мне было вот меня еще нет ему теперь когда даже вдруг если уже
    или быть был него вас нибудь опять вам ведь там потом себя ничего ней может тут где есть надо
    для тебя чем была сам чтоб без будто чего раз тоже себе будет тогда кто этот того потому этого
    какой совсем ним здесь этом один почти тем чтобы нее сейчас были куда зачем всех никогда можно
    при наконец два другой хоть после над больше тот через эти нас про всего них какая много разве
    три эту свою этой перед иногда лучше чуть том нельзя такой более всегда конечно всю между также
    который которая которые которого которой своей свой
    the and but then with from into than such not can may might will would should could has have
    had does did which who whom whose about over under also more most other some any each this
    that these those its are was were been being for
    """.split()
)


def split_sentences(text: str) -> list[str]:
    parts = (p.strip() for p in _SENTENCE_SPLIT_RE.split(text or ""))
    return [p for p in parts if p]


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "")]


def content_words(text: str, min_len: int = 4) -> list[str]:
    return [w for w in tokenize(text) if len(w) >= min_len and w not in STOPWORDS]


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Самые частые значимые слова; при равенстве — в порядке первого появления."""
    words = content_words(text)
    counts = Counter(words)
    first_seen: dict[str, int] = {}
    for index, word in enumerate(words):
        first_seen.setdefault(word, index)
    ranked = sorted(counts, key=lambda w: (-counts[w], first_seen[w]))
    return ranked[:top_n]


def summarize(text: str, max_sentences: int = 3) -> str:
    """Экстрактивное резюме: предложения с самыми «насыщенными» словами, в исходном порядке."""
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    freq = Counter(content_words(text))

    def score(sentence: str) -> float:
        words = content_words(sentence)
        if not words:
            return 0.0
        return sum(freq[w] for w in words) / math.sqrt(len(words))

    top = sorted(range(len(sentences)), key=lambda i: (-score(sentences[i]), i))[:max_sentences]
    return " ".join(sentences[i] for i in sorted(top))

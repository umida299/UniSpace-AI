import json
import re

import pytest
from samples import SAMPLE_TEXT

from unispace.ai.llm import LLMError, OfflineLLM
from unispace.models import Quiz
from unispace.services.quiz import (
    QuizGenerationError,
    generate_cloze_questions,
    generate_questions,
    grade_quiz,
)


class FakeLLM:
    name = "fake"
    offline = False

    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, 0

    def complete(self, system, messages, max_tokens=1024):
        self.calls += 1
        if self.error:
            raise self.error
        return self.reply


def test_cloze_questions_are_well_formed():
    questions = generate_cloze_questions(SAMPLE_TEXT, n=3, seed=1)
    assert len(questions) >= 2
    for q in questions:
        answer = q.options[q.answer_index]
        assert "_____" in q.prompt
        assert 3 <= len(q.options) <= 4
        assert len(set(q.options)) == len(q.options)
        assert not re.search(rf"\b{re.escape(answer)}\b", q.prompt, re.IGNORECASE)


def test_cloze_answers_are_unique():
    questions = generate_cloze_questions(SAMPLE_TEXT, n=6, seed=2)
    answers = [q.options[q.answer_index] for q in questions]
    assert len(answers) == len(set(answers))


def test_cloze_is_deterministic_with_seed():
    a = generate_cloze_questions(SAMPLE_TEXT, n=3, seed=5)
    b = generate_cloze_questions(SAMPLE_TEXT, n=3, seed=5)
    assert [(q.prompt, q.options, q.answer_index) for q in a] == [
        (q.prompt, q.options, q.answer_index) for q in b
    ]


def test_too_little_text_raises():
    with pytest.raises(QuizGenerationError):
        generate_questions("Коротко.", n=3)


def test_offline_llm_uses_heuristic():
    questions = generate_questions(SAMPLE_TEXT, n=2, llm=OfflineLLM())
    assert questions and "_____" in questions[0].prompt


def test_llm_questions_used_when_valid():
    reply = "Вот тест:\n" + json.dumps(
        {
            "questions": [
                {
                    "prompt": "Что поглощает свет?",
                    "options": ["Хлорофилл", "Глюкоза"],
                    "answer_index": 0,
                }
            ]
        },
        ensure_ascii=False,
    )
    llm = FakeLLM(reply=reply)
    questions = generate_questions(SAMPLE_TEXT, n=3, llm=llm)
    assert llm.calls == 1
    assert [q.prompt for q in questions] == ["Что поглощает свет?"]


@pytest.mark.parametrize(
    "llm",
    [
        FakeLLM(reply="не JSON"),
        FakeLLM(reply='{"questions": [{"prompt": "?", "options": ["a", "b"], "answer_index": 5}]}'),
        FakeLLM(reply='{"other": []}'),
        FakeLLM(error=LLMError("сеть недоступна")),
    ],
)
def test_bad_llm_output_falls_back_to_heuristic(llm):
    questions = generate_questions(SAMPLE_TEXT, n=2, llm=llm)
    assert llm.calls == 1
    assert questions and "_____" in questions[0].prompt


def test_grading():
    questions = generate_cloze_questions(SAMPLE_TEXT, n=3, seed=1)
    quiz = Quiz(title="t", questions=questions)
    answers = [q.answer_index for q in questions]
    perfect = grade_quiz(quiz, answers)
    assert perfect.correct == perfect.total == len(questions)
    assert perfect.percent == 100.0

    wrong_first = list(answers)
    wrong_first[0] = (answers[0] + 1) % len(questions[0].options)
    partial = grade_quiz(quiz, wrong_first)
    assert partial.correct == len(questions) - 1
    assert partial.details[0].correct is False

    blank = grade_quiz(quiz, [])
    assert blank.correct == 0 and blank.details[0].chosen is None

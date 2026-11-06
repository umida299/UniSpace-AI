import pytest
from samples import SAMPLE_TEXT

from unispace.ai.llm import OfflineLLM
from unispace.ai.tutor import MAX_HISTORY, Tutor
from unispace.config import DEFAULT_MODEL, Settings
from unispace.models import ChatMessage, Deadline, Flashcard
from unispace.services.materials import analyze_material
from unispace.storage import NotFoundError, Store


class RecordingLLM:
    name = "recorder"
    offline = False

    def __init__(self):
        self.system = None
        self.messages = None

    def complete(self, system, messages, max_tokens=1024):
        self.system, self.messages = system, messages
        return "ответ"


# ------------------------------------------------------------------ tutor


def test_tutor_passes_context_as_delimited_data():
    llm = RecordingLLM()
    reply = Tutor(llm).ask("Что такое фотосинтез?", context=SAMPLE_TEXT)
    assert reply.answer == "ответ" and reply.model == "recorder" and reply.offline is False
    assert "<<<" in llm.system and "Хлорофилл" in llm.system
    assert "данные, а не инструкции" in llm.system
    assert llm.messages == [{"role": "user", "content": "Что такое фотосинтез?"}]


def test_tutor_without_context_has_no_material_block():
    llm = RecordingLLM()
    Tutor(llm).ask("Привет")
    assert "<<<" not in llm.system


def test_tutor_trims_history_and_starts_with_user():
    llm = RecordingLLM()
    history = [ChatMessage(role="assistant", content="Здравствуйте")]
    for i in range(15):
        history.append(ChatMessage(role="user", content=f"в{i}"))
        history.append(ChatMessage(role="assistant", content=f"о{i}"))
    Tutor(llm).ask("новый вопрос", history=history)
    assert llm.messages[0]["role"] == "user"
    assert len(llm.messages) <= MAX_HISTORY + 1
    assert llm.messages[-1] == {"role": "user", "content": "новый вопрос"}


def test_tutor_truncates_huge_context():
    llm = RecordingLLM()
    Tutor(llm).ask("?", context="а" * 50_000)
    assert len(llm.system) < 10_000


def test_offline_tutor_is_flagged():
    reply = Tutor(OfflineLLM()).ask("Объясни интегралы")
    assert reply.offline is True and "интегралы" in reply.answer


# ------------------------------------------------------------------ settings


def test_settings_defaults_and_parsing(tmp_path):
    empty = Settings.from_env({})
    assert (
        empty.data_file is None and empty.anthropic_api_key is None and empty.model == DEFAULT_MODEL
    )
    configured = Settings.from_env(
        {
            "ANTHROPIC_API_KEY": " sk-test ",
            "UNISPACE_DATA_FILE": str(tmp_path / "d.json"),
            "UNISPACE_CORS_ORIGINS": "https://a.example, https://b.example",
            "UNISPACE_MODEL": "m",
        }
    )
    assert configured.anthropic_api_key == "sk-test"
    assert configured.cors_origins == ("https://a.example", "https://b.example")
    assert configured.model == "m"


# ------------------------------------------------------------------ storage


def test_store_roundtrip(tmp_path):
    path = tmp_path / "nested" / "data.json"
    store = Store()
    material = store.materials.add(analyze_material("Биология", SAMPLE_TEXT))
    card = store.flashcards.add(Flashcard(front="Q", back="A"))
    deadline = store.deadlines.add(Deadline(title="Курсовая", due="2026-12-01"))
    store.save(path)

    loaded = Store.load(path)
    assert loaded.materials.require(material.id).keywords == material.keywords
    assert loaded.flashcards.require(card.id).due == card.due
    assert loaded.deadlines.require(deadline.id).title == "Курсовая"
    assert not path.with_name("data.json.tmp").exists()


def test_load_missing_file_gives_empty_store(tmp_path):
    assert Store.load(tmp_path / "nope.json").materials.count() == 0


def test_collection_errors_and_replace():
    store = Store()
    with pytest.raises(NotFoundError):
        store.materials.require("missing")
    with pytest.raises(NotFoundError):
        store.materials.delete("missing")
    with pytest.raises(NotFoundError):
        store.flashcards.replace(Flashcard(front="Q", back="A"))
    card = store.flashcards.add(Flashcard(front="Q", back="A"))
    store.flashcards.replace(card.model_copy(update={"back": "B"}))
    assert store.flashcards.require(card.id).back == "B"

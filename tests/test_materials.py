from samples import SAMPLE_TEXT

from unispace.services.materials import analyze_material
from unispace.services.text import extract_keywords, split_sentences, summarize


def test_split_sentences():
    assert len(split_sentences(SAMPLE_TEXT)) == 6


def test_keywords_are_ranked_and_limited():
    keywords = extract_keywords(SAMPLE_TEXT, top_n=5)
    assert len(keywords) == 5
    assert "фотосинтеза" in keywords
    assert "и" not in keywords


def test_summary_is_subset_of_text_in_order():
    summary = summarize(SAMPLE_TEXT, max_sentences=2)
    sentences = split_sentences(SAMPLE_TEXT)
    parts = [s for s in sentences if s in summary]
    assert len(parts) == 2
    assert sentences.index(parts[0]) < sentences.index(parts[1])


def test_short_text_summary_returns_everything():
    assert (
        summarize("Первое предложение. Второе предложение.")
        == "Первое предложение. Второе предложение."
    )


def test_analyze_material_fills_metadata():
    material = analyze_material("Биология", SAMPLE_TEXT)
    assert material.title == "Биология"
    assert material.word_count > 30
    assert material.reading_minutes == 1
    assert material.keywords and material.summary


def test_analyze_empty_words():
    material = analyze_material("Цифры", "123 456")
    assert material.word_count == 0
    assert material.reading_minutes == 0

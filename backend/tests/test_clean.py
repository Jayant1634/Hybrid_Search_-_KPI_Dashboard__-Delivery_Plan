from app.ingest.clean import clean_text, is_too_short, split_front_matter


def test_splits_quoted_front_matter() -> None:
    raw = (
        "---\n"
        'title: "Volcano"\n'
        'source: "https://simple.wikipedia.org/wiki/Volcano"\n'
        'license: "CC BY-SA 4.0"\n'
        'topic: "volcanoes"\n'
        'fetched: "2026-09-03"\n'
        "---\n"
        "\n"
        "A volcano is a mountain that erupts lava.\n"
    )
    meta, body = split_front_matter(raw)
    assert meta == {
        "title": "Volcano",
        "source": "https://simple.wikipedia.org/wiki/Volcano",
        "license": "CC BY-SA 4.0",
        "topic": "volcanoes",
        "fetched": "2026-09-03",
    }
    assert body == "A volcano is a mountain that erupts lava."


def test_split_without_front_matter_returns_all_text() -> None:
    raw = "Just a body with no markers."
    meta, body = split_front_matter(raw)
    assert meta == {}
    assert body == raw


def test_splits_unquoted_key_values() -> None:
    raw = "---\ntitle: Mars\nsource: wiki\n---\nRed planet."
    meta, body = split_front_matter(raw)
    assert meta == {"title": "Mars", "source": "wiki"}
    assert body == "Red planet."


def test_unicode_normalise() -> None:
    decomposed = "cafe\u0301"
    assert clean_text(decomposed) == "caf\u00e9"


def test_drops_numeric_reference_markers() -> None:
    text = "Lava is hot.[1] Ash can travel far.[12] Rocks cool slowly."
    cleaned = clean_text(text)
    assert "[1]" not in cleaned
    assert "[12]" not in cleaned
    assert cleaned == "Lava is hot. Ash can travel far. Rocks cool slowly."


def test_drops_simple_wikipedia_trailing_sections() -> None:
    text = (
        "A volcano is a mountain that erupts lava and ash.\n"
        "Magma comes from deep in the Earth.\n"
        "\n"
        "References\n"
        "Smith, Jane. Volcanoes of the World.\n"
        "\n"
        "Related pages\n"
        "Lava\n"
        "Magma\n"
        "\n"
        "Other websites\n"
        "https://example.com/volcano\n"
    )
    cleaned = clean_text(text)
    assert "volcano is a mountain" in cleaned
    assert "Magma comes from deep" in cleaned
    assert "References" not in cleaned
    assert "Related pages" not in cleaned
    assert "Other websites" not in cleaned
    assert "Smith" not in cleaned
    assert "example.com" not in cleaned


def test_collapses_whitespace() -> None:
    cleaned = clean_text("A   volcano\n\nerupts.\tYes.")
    assert cleaned == "A volcano erupts. Yes."


def test_too_short_under_200_chars() -> None:
    assert is_too_short("short")
    assert is_too_short("x" * 199)
    assert not is_too_short("x" * 200)


def test_wiki_tail_can_leave_text_too_short() -> None:
    text = "Short intro.\n\nReferences\n" + ("bibliography " * 40)
    cleaned = clean_text(text)
    assert cleaned == "Short intro."
    assert is_too_short(cleaned)


def test_caps_long_doc_at_sentence_end_near_20k() -> None:
    sentence = "The river floods in spring. "
    text = sentence * 800
    cleaned = clean_text(text)
    assert 18_000 <= len(cleaned) <= 20_500
    assert cleaned.endswith(".")
    assert not cleaned.endswith("The river floods in spring")


def test_hard_caps_when_no_sentence_end() -> None:
    cleaned = clean_text("A" * 25_000)
    assert cleaned == "A" * 20_000

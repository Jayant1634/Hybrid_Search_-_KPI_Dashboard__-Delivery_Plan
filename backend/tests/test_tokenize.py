from app.search.tokenize import STOPWORDS, tokenize


def test_lowercases_tokens() -> None:
    assert tokenize("Volcano LAVA Ash") == ["volcano", "lava", "ash"]


def test_splits_on_word_characters() -> None:
    assert tokenize("magma, rock; ash!") == ["magma", "rock", "ash"]
    assert tokenize("well-known") == ["well", "known"]


def test_drops_single_char_tokens() -> None:
    assert tokenize("a volcano is x big") == ["volcano", "big"]
    assert tokenize("5 rocks") == ["rocks"]


def test_drops_stopwords() -> None:
    assert tokenize("the lava is on the rock") == ["lava", "rock"]


def test_keeps_alphanumeric_multichar_tokens() -> None:
    assert tokenize("co2 and h2o") == ["co2", "h2o"]


def test_empty_text_returns_empty_list() -> None:
    assert tokenize("") == []
    assert tokenize("the a an of to") == []


def test_stopword_list_is_reasonably_sized() -> None:
    assert 35 <= len(STOPWORDS) <= 60
    assert "the" in STOPWORDS

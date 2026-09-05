from app.ingest.split import split_sentences


def test_splits_plain_sentences() -> None:
    assert split_sentences("Lava is hot. Ash is grey.") == [
        "Lava is hot.",
        "Ash is grey.",
    ]


def test_keeps_dr_abbreviation() -> None:
    assert split_sentences("Dr. Smith went to the volcano. It erupted.") == [
        "Dr. Smith went to the volcano.",
        "It erupted.",
    ]


def test_keeps_us_abbreviation() -> None:
    assert split_sentences("The U.S. Army arrived. Rain followed.") == [
        "The U.S. Army arrived.",
        "Rain followed.",
    ]


def test_keeps_eg_abbreviation() -> None:
    assert split_sentences("See e.g. Smith (1999). Later work agreed.") == [
        "See e.g. Smith (1999).",
        "Later work agreed.",
    ]


def test_question_and_exclaim() -> None:
    assert split_sentences("It erupted! Did anyone see it? Yes.") == [
        "It erupted!",
        "Did anyone see it?",
        "Yes.",
    ]


def test_empty_and_blank() -> None:
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_single_sentence_unchanged() -> None:
    assert split_sentences("Just one sentence.") == ["Just one sentence."]

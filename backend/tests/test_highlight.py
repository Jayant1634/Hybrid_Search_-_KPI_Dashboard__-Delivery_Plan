from app.search.highlight import (
    count_occurrences,
    highlight_containing,
    make_snippet,
    term_matches_word,
)


def test_wraps_whole_word_matches_in_em() -> None:
    out = make_snippet("the volcano spewed lava", ["lava"], window=240)
    assert out == "the volcano spewed <em>lava</em>"


def test_matching_is_case_insensitive() -> None:
    out = make_snippet("Lava and LAVA everywhere", ["lava"], window=240)
    assert out == "<em>Lava</em> and <em>LAVA</em> everywhere"


def test_only_matches_whole_words() -> None:
    out = make_snippet("lava flows into lavatory", ["lava"], window=240)
    assert out == "<em>lava</em> flows into lavatory"


def test_html_escapes_text_first() -> None:
    out = make_snippet("rock & <b>lava</b>", ["lava"], window=240)
    assert out == "rock &amp; &lt;b&gt;<em>lava</em>&lt;/b&gt;"


def test_falls_back_to_start_when_no_match() -> None:
    text = "the quick brown fox jumps over the lazy dog"
    assert make_snippet(text, ["zebra"], window=240) == text


def test_fallback_truncates_long_text_with_ellipsis() -> None:
    text = "word " * 100
    out = make_snippet(text, ["missing"], window=20)
    assert out.endswith("\u2026")
    assert "<em>" not in out
    # trimmed to a whole word, no dangling partial token
    assert out[:-1].rstrip().split() == ["word", "word", "word", "word"]


def test_picks_window_with_most_matches() -> None:
    text = (
        "lava " + "x" * 300 + " here lava appears twice lava near the end"
    )
    out = make_snippet(text, ["lava"], window=60)
    # the dense cluster at the end wins over the lone early match
    assert out.count("<em>lava</em>") == 2
    assert out.startswith("\u2026")


def test_adds_leading_and_trailing_ellipsis_when_cut() -> None:
    text = "alpha beta gamma delta lava epsilon zeta eta theta iota kappa"
    out = make_snippet(text, ["lava"], window=20)
    assert out.startswith("\u2026")
    assert out.endswith("\u2026")
    assert "<em>lava</em>" in out


def test_no_trailing_ellipsis_when_window_reaches_end() -> None:
    out = make_snippet("hunting for lava now", ["lava"], window=240)
    assert not out.endswith("\u2026")
    assert out == "hunting for <em>lava</em> now"


def test_multiple_terms_all_highlighted() -> None:
    out = make_snippet("ash and lava and smoke", ["ash", "lava"], window=240)
    assert out == "<em>ash</em> and <em>lava</em> and smoke"


def test_blank_terms_are_ignored() -> None:
    text = "the quick brown fox"
    assert make_snippet(text, ["", "   "], window=240) == text


def test_regex_special_term_is_literal() -> None:
    out = make_snippet("cost is a.b dollars", ["a.b"], window=240)
    assert out == "cost is <em>a.b</em> dollars"


def test_highlight_containing_matches_shared_stem() -> None:
    out = highlight_containing("Chemical element", ["chec"])
    assert out == "<em>Chemical</em> element"


def test_term_matches_word_needs_three_shared_chars() -> None:
    assert term_matches_word("chec", "chemical")
    assert term_matches_word("lava", "lava")
    assert term_matches_word("lava", "lavatory")
    assert not term_matches_word("xyz", "chemical")
    assert not term_matches_word("ab", "about")


def test_highlight_containing_is_case_insensitive() -> None:
    out = highlight_containing("Calcium and CALCIUM", ["calcium"])
    assert out == "<em>Calcium</em> and <em>CALCIUM</em>"


def test_highlight_containing_escapes_html() -> None:
    out = highlight_containing("rock & <b>lava</b>", ["lava"])
    assert out == "rock &amp; &lt;b&gt;<em>lava</em>&lt;/b&gt;"


def test_highlight_containing_empty_terms_is_escaped_text() -> None:
    assert highlight_containing("a < b", []) == "a &lt; b"


def test_count_occurrences_counts_words_containing_term() -> None:
    text = "Calcium is a chemical element. Chemical compounds of calcium."
    counts = dict(count_occurrences(text, ["chec", "calcium"]))
    assert counts["chec"] == 2
    assert counts["calcium"] == 2


def test_count_occurrences_skips_blank_and_duplicate_terms() -> None:
    assert count_occurrences("lava lava", ["Lava", "lava", "  "]) == [("lava", 2)]

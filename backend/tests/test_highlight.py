from app.search.highlight import make_snippet


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

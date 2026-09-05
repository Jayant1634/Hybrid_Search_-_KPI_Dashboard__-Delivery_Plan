from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import generate_contracts  # noqa: E402


def test_repo_root_follows_script_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    expected = Path(generate_contracts.__file__).resolve().parent.parent
    assert generate_contracts.repo_root() == expected


def test_slugify_and_source() -> None:
    assert generate_contracts.slugify("A.T. Kearney, Inc.") == "a-t-kearney-inc"
    rng = random.Random(1)
    spec = generate_contracts.build_spec(0, rng)
    source = generate_contracts.source_for(spec)
    assert source.startswith("kearney-contracts/")
    assert spec.type_slug in source


def test_writes_front_matter_and_long_body(tmp_path: Path) -> None:
    out = tmp_path / "contracts"
    code = generate_contracts.main(
        ["--count", "3", "--seed", "7", "--out", str(out)],
        root=tmp_path,
    )
    assert code == 0
    files = sorted(p for p in out.glob("*.md") if p.name != "ATTRIBUTION.md")
    assert len(files) == 3
    text = files[0].read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert 'dataset: "contracts"' in text
    assert "kearney-contracts/" in text
    body = text.split("---", 2)[-1]
    assert len(body.strip()) >= generate_contracts.MIN_BODY_CHARS
    attribution = (out / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert len(attribution) < 200


def test_limit_zero_writes_only_attribution(tmp_path: Path) -> None:
    out = tmp_path / "contracts"
    code = generate_contracts.main(["--count", "0", "--out", str(out)], root=tmp_path)
    assert code == 0
    md = list(out.glob("*.md"))
    assert [p.name for p in md] == ["ATTRIBUTION.md"]


def test_negative_count_is_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = generate_contracts.main(["--count", "-1"], root=tmp_path)
    assert code == 1
    assert "count must be" in capsys.readouterr().err


def test_same_seed_is_deterministic() -> None:
    first = generate_contracts.generate_specs(5, 99)
    second = generate_contracts.generate_specs(5, 99)
    assert [generate_contracts.source_for(s) for s in first] == [
        generate_contracts.source_for(s) for s in second
    ]
    assert generate_contracts.render_body(first[0]) == generate_contracts.render_body(
        second[0]
    )


def test_filenames_are_unique() -> None:
    specs = generate_contracts.generate_specs(80, generate_contracts.DEFAULT_SEED)
    names = [generate_contracts.filename_for(spec) for spec in specs]
    assert len(names) == len(set(names))

import json
from pathlib import Path

from app.config import load_config


def test_sample_docs_and_tmp_repo(sample_docs_jsonl: Path, tmp_repo: Path) -> None:
    lines = sample_docs_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6
    titles = {json.loads(line)["title"] for line in lines}
    assert titles == {"Volcanoes", "Bread", "Python", "The Moon", "Football", "Jazz"}
    for name in ("raw", "processed", "index", "eval", "metrics"):
        assert (tmp_repo / "data" / name).is_dir()
    assert load_config().repo_root == tmp_repo.resolve()

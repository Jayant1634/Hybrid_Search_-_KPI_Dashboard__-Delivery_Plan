"""Run ``python -m app.callgraph`` to regenerate frontend/public/callgraph/*.json."""

from __future__ import annotations

from pathlib import Path

from app.callgraph.analyze import find_repo_root, write_callgraph_json


def main() -> None:
    repo = find_repo_root(Path(__file__))
    written = write_callgraph_json(repo)
    for path in written:
        print(path.relative_to(repo).as_posix())


if __name__ == "__main__":
    main()

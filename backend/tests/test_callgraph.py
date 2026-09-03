"""Call-graph analyzer: uncalled roots, one-level BFS, topological order."""

from __future__ import annotations

import json
from pathlib import Path

from app.callgraph.analyze import build_callgraph, find_repo_root, write_callgraph_json

_ENTRY = """\
from app.util import helper

def main() -> None:
    helper()
"""

_UTIL = """\
def helper() -> None:
    hidden()

def hidden() -> None:
    pass

def unused() -> None:
    pass
"""

_ORPHAN = """\
def ghost() -> None:
    pass
"""

_MAIN_TSX = """\
import App from './App'

export default function mount() {
  return <App />
}
"""

_APP_TSX = """\
export default function App() {
  return null
}

function Dead() {
  return null
}
"""

_DEAD_TS = """\
export function leftover() {
  return 1
}
"""


def _mini_repo(tmp_path: Path) -> Path:
    app = tmp_path / "backend" / "app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("", encoding="utf-8")
    (app / "entry.py").write_text(_ENTRY, encoding="utf-8")
    (app / "util.py").write_text(_UTIL, encoding="utf-8")
    (app / "orphan.py").write_text(_ORPHAN, encoding="utf-8")
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True)
    (src / "main.tsx").write_text(_MAIN_TSX, encoding="utf-8")
    (src / "App.tsx").write_text(_APP_TSX, encoding="utf-8")
    (src / "dead.ts").write_text(_DEAD_TS, encoding="utf-8")
    (tmp_path / "frontend" / "public" / "callgraph").mkdir(parents=True)
    return tmp_path


def test_python_cross_file_call_and_unused(tmp_path: Path) -> None:
    graph = build_callgraph(_mini_repo(tmp_path))
    helper = "backend/app/util.py::helper"
    main = "backend/app/entry.py::main"
    hidden = "backend/app/util.py::hidden"
    unused = "backend/app/util.py::unused"
    ghost = "backend/app/orphan.py::ghost"

    assert helper in graph["functions"][main]["calls"]
    assert main in graph["functions"][helper]["called_by"]
    assert hidden in graph["functions"][helper]["calls"]
    assert graph["functions"][unused]["called_by"] == []
    assert graph["functions"][ghost]["called_by"] == []
    assert hidden not in graph["uncalled_functions"]
    assert unused in graph["uncalled_functions"]
    assert main in graph["uncalled_functions"]


def test_uncalled_files_are_not_imported(tmp_path: Path) -> None:
    graph = build_callgraph(_mini_repo(tmp_path))
    assert "backend/app/entry.py" in graph["uncalled_files"]
    assert "backend/app/orphan.py" in graph["uncalled_files"]
    assert "backend/app/util.py" not in graph["uncalled_files"]
    assert "backend/app/entry.py" in graph["files"]["backend/app/util.py"]["imported_by"]


def test_bfs_one_level_does_not_include_second_hop(tmp_path: Path) -> None:
    graph = build_callgraph(_mini_repo(tmp_path))
    hops = {(h["from"], h["to"]) for h in graph["hops_functions"]}
    main = "backend/app/entry.py::main"
    helper = "backend/app/util.py::helper"
    hidden = "backend/app/util.py::hidden"
    assert (main, helper) in hops
    assert (helper, hidden) not in hops
    assert hidden not in graph["bfs_functions"]["nodes"]
    assert helper in graph["bfs_functions"]["layers"][1]


def test_topo_places_caller_before_callee(tmp_path: Path) -> None:
    graph = build_callgraph(_mini_repo(tmp_path))
    topo = graph["topo_functions"]
    main = "backend/app/entry.py::main"
    helper = "backend/app/util.py::helper"
    assert topo.index(main) < topo.index(helper)


def test_tsx_default_import_and_dead_component(tmp_path: Path) -> None:
    graph = build_callgraph(_mini_repo(tmp_path))
    mount = "frontend/src/main.tsx::mount"
    app = "frontend/src/App.tsx::App"
    dead = "frontend/src/App.tsx::Dead"
    leftover = "frontend/src/dead.ts::leftover"
    assert app in graph["functions"][mount]["calls"]
    assert dead in graph["uncalled_functions"]
    assert leftover in graph["uncalled_functions"]
    assert "frontend/src/dead.ts" in graph["uncalled_files"]
    assert "frontend/src/App.tsx" not in graph["uncalled_files"]


def test_write_callgraph_json_creates_split_files(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    written = write_callgraph_json(repo)
    names = {p.name for p in written}
    assert names == {
        "graph.json",
        "files.json",
        "functions.json",
        "uncalled.json",
        "bfs.json",
        "topo.json",
        "hops.json",
    }
    graph = json.loads((repo / "frontend" / "public" / "callgraph" / "graph.json").read_text(encoding="utf-8"))
    assert "files" in graph and "functions" in graph
    assert "topo_files" in graph and "hops_functions" in graph
    assert not str(graph["files"]).startswith("/")
    first_file = next(iter(graph["files"]))
    assert not first_file.startswith("/") and ":" not in first_file[:3]


def test_find_repo_root_and_real_hybrid_import() -> None:
    root = find_repo_root()
    graph = build_callgraph(root)
    hybrid = "backend/app/search/hybrid.py"
    assert hybrid in graph["files"]
    assert graph["files"][hybrid]["imported_by"]
    searcher = "backend/app/search/hybrid.py::HybridSearcher.search"
    assert searcher in graph["functions"]
    assert graph["stats"]["file_count"] >= 1

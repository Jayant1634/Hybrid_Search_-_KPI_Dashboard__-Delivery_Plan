"""Build file- and function-level call graphs from the repo source.

Scans ``backend/app``, ``scripts``, and ``frontend/src``. Output paths in the
JSON are posix paths relative to the repo root. Never stores absolute paths.
"""

from __future__ import annotations

import ast
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TS_KEYWORDS = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "with",
        "return",
        "typeof",
        "new",
        "void",
        "delete",
        "await",
        "yield",
        "import",
        "export",
        "from",
        "as",
        "class",
        "extends",
        "super",
        "this",
        "constructor",
        "get",
        "set",
        "of",
        "in",
        "case",
        "default",
        "else",
        "try",
        "finally",
        "throw",
        "interface",
        "type",
        "enum",
        "implements",
        "package",
        "public",
        "private",
        "protected",
        "static",
        "async",
        "let",
        "const",
        "var",
    }
)

_IMPORT_FROM_RE = re.compile(
    r"""import\s+(?:type\s+)?(?:(\w+)\s*,\s*)?\{([^}]*)\}\s*from\s*['"]([^'"]+)['"]""",
)
_IMPORT_DEFAULT_RE = re.compile(
    r"""import\s+(?:type\s+)?(\w+)\s+from\s*['"]([^'"]+)['"]""",
)
_IMPORT_STAR_RE = re.compile(
    r"""import\s+\*\s+as\s+(\w+)\s+from\s*['"]([^'"]+)['"]""",
)
_TS_FUNC_RE = re.compile(
    r"""(?:export\s+default\s+)?(?:export\s+)?(?:async\s+)?function\s+(\w+)"""
    r"""|(?:export\s+default\s+)?(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>"""
    r"""|(?:export\s+default\s+)?(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function"""
)
_CALL_RE = re.compile(r"""\b([A-Za-z_][A-Za-z0-9_]*)\s*\(""")
_JSX_RE = re.compile(r"""<([A-Z][A-Za-z0-9_]*)\b""")
_BRACE_FUNC_RE = re.compile(
    r"""(?:export\s+default\s+)?(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{"""
    r"""|(?:export\s+default\s+)?(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{"""
    r"""|(?:export\s+default\s+)?(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\([^)]*\)\s*\{"""
)


@dataclass
class _Func:
    file: str
    name: str
    qualname: str
    lineno: int
    raw_calls: list[str] = field(default_factory=list)


@dataclass
class _FileInfo:
    path: str
    language: str
    functions: list[_Func] = field(default_factory=list)
    import_paths: list[str] = field(default_factory=list)
    imported_names: dict[str, tuple[str, str]] = field(default_factory=dict)
    # local name -> (module_or_file, original_name)


def find_repo_root(start: Path | None = None) -> Path:
    """Walk parents until ``backend/app`` and ``frontend/src`` both exist."""
    cur = (start or Path(__file__)).resolve()
    if cur.is_file():
        cur = cur.parent
    for parent in [cur, *cur.parents]:
        if (parent / "backend" / "app").is_dir() and (parent / "frontend" / "src").is_dir():
            return parent
    raise FileNotFoundError("could not find repo root (backend/app + frontend/src)")


def _rel(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def iter_source_files(repo: Path) -> list[Path]:
    """Return scanned source files in deterministic order."""
    files: list[Path] = []
    app = repo / "backend" / "app"
    if app.is_dir():
        files.extend(sorted(p for p in app.rglob("*.py") if "__pycache__" not in p.parts))
    scripts = repo / "scripts"
    if scripts.is_dir():
        files.extend(sorted(scripts.glob("*.py")))
    src = repo / "frontend" / "src"
    if src.is_dir():
        files.extend(
            sorted(
                p
                for p in src.rglob("*")
                if p.suffix in {".ts", ".tsx"} and p.name != "vite-env.d.ts"
            )
        )
    return files


def _py_module(rel: str) -> str | None:
    parts = rel.split("/")
    if len(parts) >= 2 and parts[0] == "backend" and parts[1] == "app" and parts[-1].endswith(".py"):
        rest = parts[2:]
        rest[-1] = rest[-1][:-3]
        if rest[-1] == "__init__":
            rest = rest[:-1]
        return ".".join(["app", *rest]) if rest else "app"
    if len(parts) == 2 and parts[0] == "scripts" and parts[1].endswith(".py"):
        return parts[1][:-3]
    return None


def _resolve_py_from(
    current_mod: str,
    current_rel: str,
    level: int,
    module: str | None,
) -> str:
    pkg = current_mod.split(".")
    if not current_rel.endswith("/__init__.py") and not current_rel.endswith("\\__init__.py"):
        if not current_rel.endswith("__init__.py"):
            pkg = pkg[:-1]
    if level > 1:
        drop = level - 1
        pkg = pkg[: max(0, len(pkg) - drop)]
    if module:
        pkg = [*pkg, *module.split(".")]
    return ".".join(p for p in pkg if p)


def _analyze_python(rel: str, source: str, module_of: dict[str, str]) -> _FileInfo:
    info = _FileInfo(path=rel, language="python")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return info

    file_to_mod = {v: k for k, v in module_of.items()}
    current_mod = file_to_mod.get(rel, "")

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[-1]
                info.imported_names[bound] = (alias.name, alias.name.split(".")[-1])
                target = module_of.get(alias.name)
                if target:
                    info.import_paths.append(target)
        elif isinstance(node, ast.ImportFrom):
            if current_mod and node.level:
                abs_mod = _resolve_py_from(current_mod, rel, node.level, node.module)
            else:
                abs_mod = node.module or ""
            target = module_of.get(abs_mod)
            if target:
                info.import_paths.append(target)
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or alias.name
                info.imported_names[bound] = (abs_mod, alias.name)

    def add_func(qualname: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        collector = _CallCollector()
        collector.visit(node)
        info.functions.append(
            _Func(
                file=rel,
                name=qualname.split(".")[-1],
                qualname=qualname,
                lineno=node.lineno,
                raw_calls=collector.calls,
            )
        )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_func(node.name, node)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add_func(f"{node.name}.{item.name}", item)

    info.import_paths = list(dict.fromkeys(info.import_paths))
    return info


class _CallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        if name:
            self.calls.append(name)
        self.generic_visit(node)


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _call_name(func.value)
        if base:
            return f"{base}.{func.attr}"
        return func.attr
    return None


def _match_brace_end(text: str, open_idx: int) -> int:
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        elif ch in {'"', "'", "`"}:
            quote = ch
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 2
                    continue
                i += 1
        i += 1
    return n - 1


def _resolve_ts_import(repo: Path, from_file: Path, spec: str) -> str | None:
    if not spec.startswith("."):
        return None
    base = (from_file.parent / spec).resolve()
    candidates = [
        Path(str(base) + ".tsx"),
        Path(str(base) + ".ts"),
        base / "index.tsx",
        base / "index.ts",
        base,
    ]
    repo_res = repo.resolve()
    for cand in candidates:
        if cand.is_file():
            try:
                return cand.relative_to(repo_res).as_posix()
            except ValueError:
                return None
    return None


def _analyze_typescript(repo: Path, path: Path, rel: str, source: str) -> _FileInfo:
    info = _FileInfo(path=rel, language="typescript")
    for match in _IMPORT_FROM_RE.finditer(source):
        default, names, spec = match.group(1), match.group(2), match.group(3)
        target = _resolve_ts_import(repo, path, spec)
        if target:
            info.import_paths.append(target)
        if default and target:
            info.imported_names[default] = (target, "default")
        for part in names.split(","):
            part = part.strip()
            if not part or part.startswith("type "):
                continue
            piece = part.replace("type ", "").strip()
            if " as " in piece:
                orig, bound = [p.strip() for p in piece.split(" as ", 1)]
            else:
                orig, bound = piece, piece
            if orig and bound and target:
                info.imported_names[bound] = (target, orig)
    for match in _IMPORT_DEFAULT_RE.finditer(source):
        if match.group(0).startswith("import type"):
            continue
        # skip named-from forms already handled
        if "{" in match.group(0):
            continue
        name, spec = match.group(1), match.group(2)
        target = _resolve_ts_import(repo, path, spec)
        if target:
            info.import_paths.append(target)
            info.imported_names[name] = (target, "default")
    for match in _IMPORT_STAR_RE.finditer(source):
        name, spec = match.group(1), match.group(2)
        target = _resolve_ts_import(repo, path, spec)
        if target:
            info.import_paths.append(target)
            info.imported_names[name] = (target, "*")

    info.import_paths = list(dict.fromkeys(info.import_paths))

    seen_names: set[str] = set()
    for match in _TS_FUNC_RE.finditer(source):
        name = next((g for g in match.groups() if g), None)
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        lineno = source[: match.start()].count("\n") + 1
        info.functions.append(_Func(file=rel, name=name, qualname=name, lineno=lineno))

    for match in _BRACE_FUNC_RE.finditer(source):
        name = next((g for g in match.groups() if g), None)
        if not name:
            continue
        brace = match.end() - 1
        if source[brace] != "{":
            continue
        end = _match_brace_end(source, brace)
        body = source[brace : end + 1]
        raw: list[str] = []
        for cm in _CALL_RE.finditer(body):
            ident = cm.group(1)
            if ident not in _TS_KEYWORDS:
                raw.append(ident)
        for jm in _JSX_RE.finditer(body):
            raw.append(jm.group(1))
        for fn in info.functions:
            if fn.qualname == name:
                fn.raw_calls = list(dict.fromkeys(raw))
                break

    return info


def _func_id(file: str, qualname: str) -> str:
    return f"{file}::{qualname}"


def _index_functions(infos: list[_FileInfo]) -> dict[str, dict[str, str]]:
    """Map file -> {name_or_qualname -> function id}."""
    index: dict[str, dict[str, str]] = {}
    for info in infos:
        names: dict[str, str] = {}
        for fn in info.functions:
            fid = _func_id(info.path, fn.qualname)
            names[fn.qualname] = fid
            names[fn.name] = fid
            if "." in fn.qualname:
                names[fn.qualname.split(".", 1)[1]] = fid
        index[info.path] = names
    return index


def _resolve_calls(
    infos: list[_FileInfo],
    module_of: dict[str, str],
) -> dict[str, list[str]]:
    """Return function_id -> list of callee function ids."""
    file_index = _index_functions(infos)
    mod_to_file = module_of
    resolved: dict[str, list[str]] = {}

    def lookup_in_file(file: str, name: str) -> str | None:
        names = file_index.get(file, {})
        if name in names:
            return names[name]
        if "." in name:
            tail = name.rsplit(".", 1)[-1]
            if tail in names:
                return names[tail]
        return None

    for info in infos:
        for fn in info.functions:
            fid = _func_id(info.path, fn.qualname)
            callees: list[str] = []
            for raw in fn.raw_calls:
                hit = lookup_in_file(info.path, raw)
                if hit and hit != fid:
                    callees.append(hit)
                    continue
                head = raw.split(".", 1)[0]
                if head in {"self", "cls", "this"}:
                    rest = raw.split(".", 1)[1] if "." in raw else ""
                    if rest:
                        local = lookup_in_file(info.path, rest)
                        if local and local != fid:
                            callees.append(local)
                    continue
                if head in info.imported_names:
                    target_mod_or_file, orig = info.imported_names[head]
                    target_file = (
                        target_mod_or_file
                        if target_mod_or_file.endswith((".py", ".ts", ".tsx"))
                        else mod_to_file.get(target_mod_or_file, "")
                    )
                    if not target_file:
                        continue
                    attr = raw.split(".", 1)[1] if "." in raw else orig
                    if orig == "default" and "." not in raw:
                        # default import used as a function/component
                        names = file_index.get(target_file, {})
                        hit2 = names.get("default") or (
                            next(iter(names.values())) if len(names) == 1 else None
                        )
                        # prefer matching exported function of same bound name
                        hit2 = names.get(head) or names.get(orig) or hit2
                        if hit2:
                            callees.append(hit2)
                        continue
                    hit2 = lookup_in_file(target_file, attr if attr != "*" else raw)
                    if hit2:
                        callees.append(hit2)
                        continue
                    hit2 = lookup_in_file(target_file, orig)
                    if hit2:
                        callees.append(hit2)
            resolved[fid] = list(dict.fromkeys(callees))
    return resolved


def _kahn_topo(node_ids: list[str], edges: list[tuple[str, str]]) -> list[str]:
    nodes = list(dict.fromkeys(node_ids))
    node_set = set(nodes)
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for src, dst in edges:
        if src not in node_set or dst not in node_set:
            continue
        adj[src].append(dst)
        indeg[dst] += 1
    queue = deque(sorted(n for n, d in indeg.items() if d == 0))
    out: list[str] = []
    while queue:
        n = queue.popleft()
        out.append(n)
        nxt = sorted(adj[n])
        for m in nxt:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    leftover = [n for n in nodes if n not in out]
    return out + leftover


def _bfs_one_level(
    outgoing: dict[str, list[str]],
    roots: list[str],
) -> dict[str, Any]:
    layer0 = list(roots)
    seen = set(layer0)
    layer1: list[str] = []
    edges: list[tuple[str, str]] = []
    hops: list[dict[str, str]] = []
    for src in layer0:
        for dst in outgoing.get(src, []):
            edges.append((src, dst))
            hops.append({"from": src, "to": dst})
            if dst not in seen:
                seen.add(dst)
                layer1.append(dst)
    nodes = layer0 + layer1
    topo = _kahn_topo(nodes, edges)
    return {
        "roots": layer0,
        "layers": [layer0, layer1],
        "edges": [{"from": a, "to": b} for a, b in edges],
        "hops": hops,
        "topo": topo,
        "nodes": nodes,
    }


def build_callgraph(repo: Path) -> dict[str, Any]:
    """Analyse ``repo`` and return the combined call-graph document."""
    repo = repo.resolve()
    sources = iter_source_files(repo)
    rels = [_rel(repo, p) for p in sources]
    module_of: dict[str, str] = {}
    for rel in rels:
        mod = _py_module(rel)
        if mod:
            module_of[mod] = rel

    infos: list[_FileInfo] = []
    errors: list[dict[str, str]] = []
    for path, rel in zip(sources, rels, strict=True):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append({"file": rel, "error": str(exc)})
            continue
        if path.suffix == ".py":
            infos.append(_analyze_python(rel, text, module_of))
        else:
            infos.append(_analyze_typescript(repo, path, rel, text))

    func_calls = _resolve_calls(infos, module_of)

    files_out: dict[str, Any] = {}
    functions_out: dict[str, Any] = {}
    imported_by: dict[str, list[str]] = defaultdict(list)
    file_call_edges: dict[str, set[str]] = defaultdict(set)

    for info in infos:
        for dest in info.import_paths:
            imported_by[dest].append(info.path)
            file_call_edges[info.path].add(dest)

    called_by_fn: dict[str, list[str]] = defaultdict(list)
    for src, dests in func_calls.items():
        src_file = src.split("::", 1)[0]
        for dst in dests:
            called_by_fn[dst].append(src)
            dst_file = dst.split("::", 1)[0]
            if dst_file != src_file:
                file_call_edges[src_file].add(dst_file)

    file_called_by: dict[str, list[str]] = defaultdict(list)
    for src, dests in file_call_edges.items():
        for dst in dests:
            file_called_by[dst].append(src)

    for info in infos:
        fn_ids = [_func_id(info.path, fn.qualname) for fn in info.functions]
        calls_files = sorted(file_call_edges.get(info.path, set()))
        files_out[info.path] = {
            "language": info.language,
            "functions": fn_ids,
            "imports": list(info.import_paths),
            "imported_by": list(dict.fromkeys(imported_by.get(info.path, []))),
            "calls": calls_files,
            "called_by": list(dict.fromkeys(file_called_by.get(info.path, []))),
        }
        for fn in info.functions:
            fid = _func_id(info.path, fn.qualname)
            functions_out[fid] = {
                "file": info.path,
                "name": fn.name,
                "qualname": fn.qualname,
                "lineno": fn.lineno,
                "calls": func_calls.get(fid, []),
                "called_by": list(dict.fromkeys(called_by_fn.get(fid, []))),
            }

    uncalled_files = sorted(
        p for p, meta in files_out.items() if not meta["called_by"] and not meta["imported_by"]
    )
    uncalled_functions = sorted(
        fid for fid, meta in functions_out.items() if not meta["called_by"]
    )

    file_outgoing = {p: meta["calls"] for p, meta in files_out.items()}
    fn_outgoing = {fid: meta["calls"] for fid, meta in functions_out.items()}

    bfs_files = _bfs_one_level(file_outgoing, uncalled_files)
    bfs_functions = _bfs_one_level(fn_outgoing, uncalled_functions)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {
            "file_count": len(files_out),
            "function_count": len(functions_out),
            "uncalled_file_count": len(uncalled_files),
            "uncalled_function_count": len(uncalled_functions),
            "file_edge_count": sum(len(v) for v in file_outgoing.values()),
            "function_edge_count": sum(len(v) for v in fn_outgoing.values()),
        },
        "files": files_out,
        "functions": functions_out,
        "uncalled_files": uncalled_files,
        "uncalled_functions": uncalled_functions,
        "bfs_files": bfs_files,
        "bfs_functions": bfs_functions,
        "topo_files": bfs_files["topo"],
        "topo_functions": bfs_functions["topo"],
        "hops_files": bfs_files["hops"],
        "hops_functions": bfs_functions["hops"],
        "errors": errors,
    }


def write_callgraph_json(repo: Path, out_dir: Path | None = None) -> list[Path]:
    """Write split and combined JSON files. Returns written paths."""
    repo = repo.resolve()
    graph = build_callgraph(repo)
    dest = out_dir if out_dir is not None else repo / "frontend" / "public" / "callgraph"
    dest.mkdir(parents=True, exist_ok=True)

    payloads: dict[str, Any] = {
        "graph.json": graph,
        "files.json": {
            "generated_at": graph["generated_at"],
            "files": graph["files"],
        },
        "functions.json": {
            "generated_at": graph["generated_at"],
            "functions": graph["functions"],
        },
        "uncalled.json": {
            "generated_at": graph["generated_at"],
            "files": graph["uncalled_files"],
            "functions": graph["uncalled_functions"],
        },
        "bfs.json": {
            "generated_at": graph["generated_at"],
            "files": graph["bfs_files"],
            "functions": graph["bfs_functions"],
        },
        "topo.json": {
            "generated_at": graph["generated_at"],
            "files": graph["topo_files"],
            "functions": graph["topo_functions"],
        },
        "hops.json": {
            "generated_at": graph["generated_at"],
            "files": graph["hops_files"],
            "functions": graph["hops_functions"],
        },
    }
    written: list[Path] = []
    for name, payload in payloads.items():
        path = dest / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written

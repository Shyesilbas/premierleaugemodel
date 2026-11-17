#!/usr/bin/env python3
"""Docs drift check for premierLeaugeModelApp.

Reports:
  MAP     docs/**/*.md files missing from docs/README.md
  LINK    relative markdown links whose target does not exist
  SYMBOL  backticked CamelCase names not declared in Python/JS source or allowlist
  SIZE    module hub README.md (src or frontend/src), AGENTS.md or SKILL.md over word budget
  STALE   references to retired root docs or moved docs/reports outputs

Usage: python3 scripts/check_docs.py [--no-class]
Exit code 1 when anything is reported.
"""
import ast
import fnmatch
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    "node_modules",
    "dist",
    "build",
    ".git",
    ".idea",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "graphify-out",
    ".claude",
    "archive",
}

SKIP_ROOT_DIRS = {"data", "models"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE_RE = re.compile(r"`([^`\n]+)`")
CAMEL_RE = re.compile(r"^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+$")
FENCE_RE = re.compile(r"^```.*?^```", re.S | re.M)
TS_DECL_RE = re.compile(r"\b(?:function|const|class|type|interface)\s+([A-Z]\w*)")
TS_IMPORT_BRACE_RE = re.compile(r"import\s+(?:type\s+)?\{([^}]+)\}\s+from")
TS_IMPORT_DEFAULT_RE = re.compile(r"import\s+([A-Z]\w*)\s+from")
STALE_ROOT_DOC_RE = re.compile(
    r"(?<![/\w])(?:AI_CONTEXT\.md|ARTIFACT_REGISTRY\.md|PROJECT_STATUS\.md|GOAL_MODELS_ANALYSIS\.md|VERI_VE_GOSTERIM_KATALOGU\.md)\b"
)
MOVED_REPORT_RE = re.compile(
    r"docs/reports/(?:README\.md|model_benchmarks\.md|data_quality\.md|team_tactical_data_audit\.md"
    r"|team_scenario_validation\.md|prospective_1x2_scorecard\.json|1x2_lineup_feature_pilot\.md"
    r"|1x2_model_audit\.md|repository_audit\.md|scripts_audit\.md|paper_trading_protocol_2026_27\.md"
    r"|experiments/|models/[^\s`)\"']+\.json)"
)

ALLOW_TERMS = {
    "FastAPI",
    "PoissonRegressor",
    "LogisticRegression",
    "StandardScaler",
    "SimpleImputer",
    "NegativeBinomial",
    "Opta",
    "PulseLive",
    "TheStatsAPI",
    "TheStatsApi",
    "TheSportsDB",
    "Transfermarkt",
    "TypeScript",
    "Tailwind",
    "TailwindCSS",
    "Lucide",
    "JavaScript",
    "SQLite",
    "PlusJakartaSans",
    "JetBrains",
    "ValueError",
    "FileNotFoundError",
    "RuntimeError",
    "LookupError",
    "KeyError",
    "TypeError",
    "AssertionError",
    "ProblemDetail",
    "OutboxEvent",
    "TestClient",
    "AbortController",
    "Vite",
    "Caddyfile",
    "YouTube",
    "PlayOff",
    "LogLoss",
    "TimeSeriesSplit",
    "Ridge",
    "ElasticNet",
    "NaN",
}

MODULE_ROOT = ROOT / "src"
FRONTEND_MODULE_ROOT = ROOT / "frontend" / "src"
HUB_WORD_BUDGET = 450
FE_HUB_WORD_BUDGET = 450
SKILL_WORD_BUDGET = 700
AGENTS_WORD_BUDGET = 600
DOC_WORD_WARN = 2500


def _prune_dirs(root: str, dirs: list[str]) -> list[str]:
    root_path = Path(root)
    return [d for d in dirs if d not in SKIP_DIRS and not (root_path == ROOT and d in SKIP_ROOT_DIRS)]


def walk(base: Path, pattern: str):
    if not base.exists():
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = _prune_dirs(root, dirs)
        for f in sorted(files):
            if fnmatch.fnmatch(f, pattern):
                yield Path(root) / f


def doc_files():
    files = set(walk(ROOT / "docs", "*.md"))
    files |= set(walk(ROOT / "reports", "*.md"))
    files |= {ROOT / "README.md", ROOT / "AGENTS.md"}
    files |= set(walk(ROOT / "src", "*.md"))
    files |= set(walk(ROOT / "frontend", "*.md"))
    files |= set(walk(ROOT / ".agents", "*.md")) if (ROOT / ".agents").exists() else set()
    return sorted(f for f in files if f.exists())


def known_symbols():
    names = set(ALLOW_TERMS)
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = _prune_dirs(root, dirs)
        for f in files:
            p = Path(root) / f
            ext = p.suffix
            if ext == ".py":
                names.add(p.stem)
                text = p.read_text(encoding="utf-8", errors="ignore")
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        names.add(node.name)
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            names.add(alias.asname or alias.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            names.add((alias.asname or alias.name).split(".")[0])
            elif ext in (".ts", ".tsx", ".js", ".jsx"):
                names.add(p.stem)
                text = p.read_text(encoding="utf-8", errors="ignore")
                names.update(TS_DECL_RE.findall(text))
                names.update(TS_IMPORT_DEFAULT_RE.findall(text))
                for block in TS_IMPORT_BRACE_RE.findall(text):
                    for item in block.split(","):
                        clean = re.sub(r"^\s*type\s+", "", item).strip()
                        if clean:
                            parts = clean.split(" as ")
                            names.add(parts[-1].strip())
    return names


def check_map(out):
    docs_root = ROOT / "docs"
    readme = docs_root / "README.md"
    if not readme.exists():
        out.append(("MAP", docs_root, 0, "docs/README.md is missing"))
        return
    text = readme.read_text(encoding="utf-8")
    linked = set()
    for target in LINK_RE.findall(text):
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        file_part = target.split("#")[0]
        if not file_part:
            continue
        resolved = (docs_root / file_part).resolve()
        if resolved.is_relative_to(docs_root):
            linked.add(resolved.relative_to(docs_root).as_posix())
    for p in sorted(walk(docs_root, "*.md")):
        rel = p.relative_to(docs_root).as_posix()
        if rel != "README.md" and rel not in linked:
            out.append(("MAP", p, 0, f"docs/{rel} is not linked from docs/README.md"))


def check_file(path: Path, text: str, symbols, out):
    is_audit_skill = path == ROOT / ".agents" / "skills" / "docs-drift-audit" / "SKILL.md"
    is_frozen_audit = path.is_relative_to(ROOT / "reports" / "audits")
    prose = FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    for lineno, line in enumerate(prose.splitlines(), 1):
        for target in LINK_RE.findall(line):
            if re.match(r"^(https?:|mailto:|#)", target):
                continue
            file_part = target.split("#")[0]
            base = ROOT / file_part.lstrip("/") if file_part.startswith("/") else path.parent / file_part
            if file_part and not base.exists():
                out.append(("LINK", path, lineno, f"broken link -> {target}"))
        if symbols is not None and not is_frozen_audit:
            for code in CODE_RE.findall(line):
                stripped = code.strip()
                token = re.split(r"[.(<#:\s\[/]", stripped, maxsplit=1)[0]
                if CAMEL_RE.match(token) and token not in symbols:
                    out.append(("SYMBOL", path, lineno, f"`{token}` not found in code"))
        if not is_audit_skill and not is_frozen_audit:
            m = STALE_ROOT_DOC_RE.search(line)
            if m:
                out.append(("STALE", path, lineno, f"retired root doc `{m.group(0)}`; update to docs/ or reports/"))
            m2 = MOVED_REPORT_RE.search(line)
            if m2:
                out.append(("STALE", path, lineno, f"moved report path `{m2.group(0)}`; update to reports/ or docs/"))


def check_sizes(out):
    budgets = [(p, HUB_WORD_BUDGET) for p in sorted(MODULE_ROOT.glob("*/README.md"))]
    budgets += [(p, FE_HUB_WORD_BUDGET) for p in sorted(FRONTEND_MODULE_ROOT.glob("*/README.md"))]
    budgets.append((ROOT / "AGENTS.md", AGENTS_WORD_BUDGET))
    budgets += [(p, SKILL_WORD_BUDGET) for p in sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md"))]
    for path, budget in budgets:
        if not path.exists():
            continue
        words = len(path.read_text(encoding="utf-8").split())
        if words > budget:
            out.append(("SIZE", path, 0, f"{words} words > budget {budget}; move detail to docs/ or references/"))


def warn_large_docs():
    warns = []
    for p in sorted(walk(ROOT / "docs", "*.md")):
        words = len(p.read_text(encoding="utf-8").split())
        if words > DOC_WORD_WARN:
            warns.append(f"WARN  {p.relative_to(ROOT)}  {words} words > {DOC_WORD_WARN}; consider splitting")
    return warns


def main() -> int:
    symbols = None if "--no-class" in sys.argv else known_symbols()
    out = []
    check_map(out)
    check_sizes(out)
    files = doc_files()
    for path in files:
        check_file(path, path.read_text(encoding="utf-8"), symbols, out)
    for kind, path, lineno, msg in out:
        loc = f"{path.relative_to(ROOT)}:{lineno}" if lineno else str(path.relative_to(ROOT))
        print(f"{kind:6} {loc}  {msg}")
    for w in warn_large_docs():
        print(w)
    print(f"\n{len(out)} issue(s) in {len(files)} files")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Zero-Emoji Standard Linter.

Scans project source code, documentation, scripts, and configuration files
to strictly enforce the zero-emoji invariant (AGENTS.md & restrained-ui-design-standard).

Usage:
    python3 scripts/check_no_emoji.py

Exit code:
    0 on clean codebase.
    1 when any emoji or prohibited pictograph is detected.
"""
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

CHECK_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".md",
    ".yml",
    ".yaml",
    ".sh",
}

ROOT_NAMED_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CODEX.md",
    ".cursorrules",
    ".clinerules",
    ".windsurfrules",
}

EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F]"  # emoticons
    r"|[\U0001F300-\U0001F5FF]"  # symbols & pictographs
    r"|[\U0001F680-\U0001F6FF]"  # transport & map
    r"|[\U0001F1E0-\U0001F1FF]"  # regional indicator symbols / flags
    r"|[\U00002702-\U000027B0]"  # dingbats
    r"|[\U0001F900-\U0001F9FF]"  # supplemental symbols and pictographs
    r"|[\U0001FA70-\U0001FAFF]"  # symbols and pictographs extended-a
    r"|[\U00002600-\U000026FF]"  # miscellaneous symbols
)


def collect_files():
    for root, dirs, files in os.walk(ROOT):
        root_path = Path(root)
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS and not (root_path == ROOT and d in SKIP_ROOT_DIRS)
        ]
        for f in sorted(files):
            path = Path(root) / f
            if path.suffix in CHECK_EXTENSIONS or f in ROOT_NAMED_FILES:
                yield path


def main() -> int:
    findings = []
    files_checked = 0

    for path in collect_files():
        files_checked += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            print(f"Warning: Could not read {path}: {exc}", file=sys.stderr)
            continue

        for lineno, line in enumerate(text.splitlines(), 1):
            matches = EMOJI_PATTERN.findall(line)
            if matches:
                rel = path.relative_to(ROOT)
                findings.append((rel, lineno, matches, line.strip()))

    if findings:
        print(f"[FAIL] Found {len(findings)} emoji violation(s) across {files_checked} files:")
        for rel, lineno, emojis, sample in findings:
            joined = ", ".join(repr(e) for e in emojis)
            print(f"  {rel}:{lineno} -> {joined} in: {sample[:80]}")
        print("\nMandatory Rule: Zero emojis in code, comments, UI text, reports, or commits.")
        return 1

    print(f"[SUCCESS] Zero emojis found across {files_checked} checked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

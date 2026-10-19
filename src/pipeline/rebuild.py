"""The one ordered chain that rebuilds every derived dataset from the raw cache.

Shared by the cron sync (``sync_season_data``) and the weekly ``run_full_pipeline`` so
both leave the same state behind. Each step runs as its own interpreter (clean memory,
no ``sys.argv`` leakage) and inherits the environment, including ``PLM_DATA_DIR``.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Iterable

from src.config import ROOT

logger = logging.getLogger("rebuild")

# name -> module and arguments. Order matters: features read the xG table, the
# database step reads the parquet files the first step wrote.
STEPS: dict[str, tuple[str, list[str]]] = {
    "process": ("src.processing.process_season_data", ["--season-name", "all"]),
    "player_index": ("src.processing.build_player_index", []),
    "features": ("src.features.build_features", []),
    "database": ("src.db.database", []),
}


class RebuildError(RuntimeError):
    """A rebuild step failed; later steps were not run, so derived data may be partial."""


def rebuild_derived_data(skip: Iterable[str] = ()) -> None:
    """Run every step in order, stopping at the first failure."""
    skip = set(skip)
    unknown = skip - set(STEPS)
    if unknown:
        raise ValueError(f"Unknown rebuild step(s) {sorted(unknown)}; choose from {list(STEPS)}")
    for name, (module, args) in STEPS.items():
        if name in skip:
            continue
        command = [sys.executable, "-m", module, *args]
        logger.info("Rebuild step %s: %s", name, " ".join(command))
        try:
            subprocess.run(command, cwd=ROOT, check=True)
        except subprocess.CalledProcessError as exc:
            raise RebuildError(f"Rebuild step '{name}' failed with exit code {exc.returncode}") from exc


def main() -> int:
    import argparse

    from src.config import configure_logging

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip", default="", help=f"comma-separated steps to leave out: {', '.join(STEPS)}")
    args = parser.parse_args()
    configure_logging()
    try:
        rebuild_derived_data(skip=[part.strip() for part in args.skip.split(",") if part.strip()])
    except (RebuildError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

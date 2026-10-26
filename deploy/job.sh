#!/usr/bin/env bash
# Usage: job.sh <name> <command...>
# Jobs share one lock (they all rewrite the parquet/DB) and the API restarts only if data changed.
cd /opt/plm || exit 1
name=$1; shift
mkdir -p logs
stamp() { stat -c %Y data/football.db data/premier_league.db data/competitions/premier_league/processed/features_matches_all.parquet 2>/dev/null; }
before=$(stamp)
flock -w 600 /tmp/plm.lock "$@" >> "logs/$name.log" 2>&1
rc=$?
[ "$rc" -ne 0 ] && echo "$(date -u +%FT%TZ) $name FAILED (exit $rc)" >> logs/failures.log
[ "$before" != "$(stamp)" ] && systemctl restart plm-api
exit "$rc"

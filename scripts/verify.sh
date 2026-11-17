#!/usr/bin/env bash
# ==============================================================================
# verify.sh — Unified Pre-Commit & CI Verification Script
#
# Runs canonical repository consistency checks:
#   1. Zero-Emoji Standard (scripts/check_no_emoji.py)
#   2. Docs Drift, Broken Links, Symbol Parity & Word Budgets (scripts/check_docs.py)
#   3. Frontend / FastAPI Endpoint Parity (scripts/check_api_endpoints.py)
#   4. Core Docs, CLI Help & Config Tests
#   5. Frontend Design Standard, Lint & Build (npm run lint:design && npm run lint && npm run build)
#
# Usage:
#   ./scripts/verify.sh             # Full suite
#   ./scripts/verify.sh --no-lint   # Skip frontend lint & build checks
#
# Exit code: 0 if all pass, 1 if any check fails.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

SKIP_LINT=0
for arg in "$@"; do
    case "$arg" in
        --no-lint)
            SKIP_LINT=1
            ;;
        --help|-h)
            echo "Usage: $0 [--no-lint]"
            exit 0
            ;;
    esac
done

echo -e "${BOLD}${BLUE}=== Running premierLeaugeModelApp Unified Verification Suite ===${NC}\n"

FAILED=0

echo -e "${BOLD}[1/5] Checking Zero-Emoji Standard...${NC}"
if python3 "${REPO_ROOT}/scripts/check_no_emoji.py"; then
    echo -e "${GREEN}PASS: Zero-Emoji Standard${NC}\n"
else
    echo -e "${RED}FAIL: Zero-Emoji violations detected${NC}\n"
    FAILED=1
fi

echo -e "${BOLD}[2/5] Checking Documentation Drift, Links, Symbols & Budgets...${NC}"
if python3 "${REPO_ROOT}/scripts/check_docs.py"; then
    echo -e "${GREEN}PASS: Docs & Links Drift${NC}\n"
else
    echo -e "${RED}FAIL: Docs drift, broken links, or budget errors detected${NC}\n"
    FAILED=1
fi

echo -e "${BOLD}[3/5] Checking Frontend / FastAPI Endpoint Parity...${NC}"
if python3 "${REPO_ROOT}/scripts/check_api_endpoints.py"; then
    echo -e "${GREEN}PASS: API Endpoint Parity${NC}\n"
else
    echo -e "${RED}FAIL: API endpoint mismatch detected${NC}\n"
    FAILED=1
fi

echo -e "${BOLD}[4/5] Running Core Docs, CLI & Config Tests...${NC}"
if (cd "${REPO_ROOT}" && PYTHONPATH=. python3 -m pytest tests/test_docs.py tests/test_cli_help.py tests/test_config.py -q); then
    echo -e "${GREEN}PASS: Core Docs, CLI & Config Tests${NC}\n"
else
    echo -e "${RED}FAIL: Core docs, CLI, or config tests failed${NC}\n"
    FAILED=1
fi

if [ "$SKIP_LINT" -eq 0 ]; then
    echo -e "${BOLD}[5/5] Checking Frontend Design Standard, Lint & Build...${NC}"
    if (cd "${REPO_ROOT}/frontend" && npm run lint:design && npm run lint && npm run build); then
        echo -e "${GREEN}PASS: Frontend Design Standard, Lint & Build${NC}\n"
    else
        echo -e "${RED}FAIL: Frontend lint, design, or build errors detected${NC}\n"
        FAILED=1
    fi
else
    echo -e "${BOLD}[5/5] Skipping Frontend Checks (--no-lint specified)${NC}\n"
fi

if [ "$FAILED" -eq 0 ]; then
    echo -e "${BOLD}${GREEN}All verification checks PASSED successfully!${NC}"
    exit 0
else
    echo -e "${BOLD}${RED}Verification FAILED. Please resolve the errors above.${NC}"
    exit 1
fi

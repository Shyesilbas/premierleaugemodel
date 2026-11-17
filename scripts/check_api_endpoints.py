#!/usr/bin/env python3
"""Check frontend API route parity against FastAPI declarations in src/api/."""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "src" / "api"
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

ROUTE_DECORATOR_RE = re.compile(
    r'@(?:router|app)\.(?:get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']'
)
FRONTEND_CALL_RE = re.compile(
    r'["\']((?:/api/)[^"\'\s?]*)["\']'
    r'|`(?:[^`]*?)((?:/api/)[^`\s?]*)[^`]*`'
)


def extract_backend_routes() -> list[str]:
    routes = []
    files = [API_DIR / "server.py"] + sorted((API_DIR / "routes").glob("*.py"))
    for p in files:
        if not p.exists():
            continue
        for path in ROUTE_DECORATOR_RE.findall(p.read_text(encoding="utf-8")):
            if path not in routes:
                routes.append(path)
    return routes


def extract_frontend_routes() -> list[str]:
    routes = []
    for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        for p in sorted(FRONTEND_SRC.rglob(ext)):
            for raw_line in p.read_text(encoding="utf-8").splitlines():
                stripped = raw_line.strip()
                if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                    continue
                for m1, m2 in FRONTEND_CALL_RE.findall(raw_line):
                    raw = m1 or m2
                    if raw.endswith("/*") or raw == "/api/":
                        continue
                    norm = re.sub(r"\$\{[^}]*(?:query|param)[^}]*\}$", "", raw, flags=re.IGNORECASE)
                    norm = re.sub(r"\$\{[^}]+\}", "{param}", norm).rstrip("/")
                    if norm and norm not in routes:
                        routes.append(norm)
    return routes


def path_to_regex(path: str) -> re.Pattern:
    norm = re.sub(r"\{[^}]+\}", "{param}", path)
    escaped = re.escape(norm).replace(r"\{param\}", r"[^/]+")
    return re.compile(f"^{escaped}$")


def main() -> int:
    print("Scanning FastAPI routes...")
    backend_routes = extract_backend_routes()
    print(f"Found {len(backend_routes)} FastAPI endpoint(s).")

    print("Extracting frontend API calls...")
    frontend_routes = extract_frontend_routes()
    print(f"Found {len(frontend_routes)} frontend API call(s).")

    patterns = [(route, path_to_regex(route)) for route in backend_routes]
    missing = []
    for fe_route in frontend_routes:
        probe = re.sub(r"\{param\}", "sample_id", fe_route)
        if not any(regex.match(probe) for _, regex in patterns):
            missing.append(fe_route)

    if missing:
        print(f"\n[FAIL] Found {len(missing)} unresolved frontend API endpoint(s):")
        for ep in sorted(missing):
            print(f"  - {ep}")
        return 1

    print("\n[SUCCESS] All frontend API calls match FastAPI route declarations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("ADMIN_TOKEN", "")
PATHS = [
    "/api/v1/production-verification/verify/",
    "/api/v1/admin-integration/readiness/",
    "/api/v1/billing/readiness/",
    "/api/v1/auth/readiness/",
    "/api/v1/ops/ready/",
]


def fetch(path):
    request = urllib.request.Request(BASE_URL + path)
    if TOKEN:
        request.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, response.read().decode("utf-8")[:500]


def main():
    results = []
    ok = True
    for path in PATHS:
        try:
            status, body = fetch(path)
            passed = 200 <= status < 500
            ok = ok and passed
            results.append({"path": path, "status": status, "ok": passed, "body_preview": body})
        except Exception as exc:
            ok = False
            results.append({"path": path, "status": None, "ok": False, "error": str(exc)})
    print(json.dumps({"base_url": BASE_URL, "ok": ok, "results": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

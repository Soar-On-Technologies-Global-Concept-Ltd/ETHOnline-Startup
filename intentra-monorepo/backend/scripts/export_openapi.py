"""Freezes the API surface: writes openapi.json and shared/openapi.json.

    python scripts/export_openapi.py
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

os.environ.setdefault("ENV", "test")
os.environ.setdefault("PRIVY_MODE", "fake")
os.environ.setdefault("WORLD_MODE", "fake")
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("WORKERS_ENABLED", "false")

from app.main import app  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> None:
    spec = app.openapi()
    for path in (ROOT / "openapi.json", ROOT / "shared/openapi.json"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(spec, indent=2) + "\n")
        print(f"wrote {path.relative_to(ROOT)} ({len(spec['paths'])} paths)")


if __name__ == "__main__":
    main()

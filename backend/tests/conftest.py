"""Pytest configuration: ensure `backend` is on sys.path when run from repo root."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# `models.database` requires DATABASE_URL at import time; default to SQLite for tests.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# `FinanceReconciler` constructs a Gemini client at init; tests mock LLM calls.
os.environ.setdefault("GEMINI_API_KEY", "test-placeholder-not-used-when-mocked")

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

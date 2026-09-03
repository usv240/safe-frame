"""Shared test setup.

The rate limiter is deliberately in-process, which is right for the product and
wrong for a test suite: its counters are module state that accumulates across
tests, so a file with enough cases starts returning 429 partway through and the
failure looks like a bug in whatever test happened to cross the threshold. It
did exactly that once the bring-your-own-clip tests were added.

Clearing the buckets before each test keeps every case independent, and leaves
the limiter itself under test where it belongs, in `tests/test_live_api.py`.
"""

from __future__ import annotations

import pytest

from safe_frame import main as main_module


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    main_module._CALLS.clear()

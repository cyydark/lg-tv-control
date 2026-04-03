"""pytest configuration: set up bscpylgtv import path once for all tests."""
import sys

# Try normal import first, then fall back to common macOS Python 3.9 path.
for _p in [None, "/Users/chenyanyu/Library/Python/3.9/lib/python/site-packages"]:
    if _p:
        sys.path.insert(0, _p)
    try:
        import bscpylgtv  # noqa: F401
        break
    except ImportError:
        if _p:
            sys.path.remove(_p)
# If not found, tests will fail with a clear import error — acceptable for unit tests.

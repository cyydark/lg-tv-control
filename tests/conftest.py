"""pytest configuration: set up bscpylgtv import path once for all tests."""
import sys
import os
import glob

_FOUND_BSCPY = False
for _p in [None]:
    try:
        import bscpylgtv  # noqa: F401
        _FOUND_BSCPY = True
        break
    except ImportError:
        pass

if not _FOUND_BSCPY:
    _home = os.path.expanduser("~")
    _SEARCH_PATTERNS = [
        f"{_home}/Library/Python/*/lib/python/*/site-packages",
        f"{_home}/Library/Python/*/lib/python/site-packages",
        "/Library/Python/*/lib/python/site-packages",
        "/usr/local/lib/python*/site-packages",
        "/opt/homebrew/lib/python*/site-packages",
    ]
    for _pattern in _SEARCH_PATTERNS:
        for _site_dir in glob.glob(_pattern):
            if not os.path.isdir(_site_dir) or _site_dir in sys.path:
                continue
            sys.path.insert(0, _site_dir)
            try:
                import bscpylgtv  # noqa: F401
                _FOUND_BSCPY = True
                break
            except ImportError:
                if _site_dir in sys.path:
                    sys.path.remove(_site_dir)
        if _FOUND_BSCPY:
            break
# If not found, tests fail with a clear import error — acceptable for unit tests.

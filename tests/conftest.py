"""pytest configuration: set up bscpylgtv import path once for all tests."""
import sys
import os
import subprocess

# Try normal import first (fast path if current Python has it)
try:
    import bscpylgtv  # noqa: F401
except ImportError:
    if not os.environ.get("BSCPY_SELF"):
        # Search PATH for a Python that has bscpylgtv and inject its site-packages
        seen = set()
        for _dir in os.environ.get("PATH", "").split(os.pathsep):
            if not _dir or _dir in seen:
                continue
            seen.add(_dir)
            for _name in ("python3", "python"):
                _exe = os.path.join(_dir, _name)
                if not os.path.isfile(_exe) or _exe in seen:
                    continue
                seen.add(_exe)
                if subprocess.run([_exe, "-c", "import bscpylgtv"],
                                  capture_output=True, timeout=10).returncode == 0:
                    # Found one — get its site-packages and add to sys.path
                    result = subprocess.run(
                        [_exe, "-c", "import site; print(site.getusersitepackages())"],
                        capture_output=True, text=True, timeout=10,
                    )
                    _sp = result.stdout.strip()
                    if _sp and _sp not in sys.path:
                        sys.path.insert(0, _sp)
                    break
            try:
                import bscpylgtv  # noqa: F401
                break
            except ImportError:
                pass
# If not found, tests fail with a clear import error — acceptable for unit tests.

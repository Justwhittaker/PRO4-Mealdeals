"""NUC supervisor import when started the way Compose starts it."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_supervisor_imports_app_when_started_by_absolute_path() -> None:
    """`python /app/scripts/celery_nuc_supervisor.py` must import app.

    That invocation puts ``scripts/`` on ``sys.path[0]``. The module inserts
    the backend root itself, so the caller does not need ``PYTHONPATH``.
    """
    script = Path(__file__).resolve().parents[1] / "scripts" / "celery_nuc_supervisor.py"
    backend = script.parent.parent
    probe = textwrap.dedent(
        f"""
        import sys
        from pathlib import Path

        script = Path({str(script)!r})
        backend = {str(backend)!r}
        sys.path = [entry for entry in sys.path if entry not in ("", backend)]
        sys.path.insert(0, str(script.parent))
        try:
            import app  # noqa: F401
        except ModuleNotFoundError:
            pass
        else:
            raise SystemExit("app was already importable; probe is not isolated")
        source = script.read_text(encoding="utf-8")
        namespace = {{
            "__name__": "celery_nuc_supervisor",
            "__file__": str(script),
            "__package__": None,
        }}
        exec(compile(source, str(script), "exec"), namespace)
        if namespace.get("APP_USER") != "appuser":
            raise SystemExit("supervisor module did not finish importing")
        """
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path("/tmp"),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout

"""The NUC image must not copy local secret env files."""

from __future__ import annotations

from pathlib import Path


def _patterns() -> set[str]:
    text = Path(__file__).resolve().parents[1].joinpath(".dockerignore").read_text(
        encoding="utf-8"
    )
    return {
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def test_dockerignore_excludes_script_env_and_other_secrets() -> None:
    patterns = _patterns()
    assert "scripts/*.env" in patterns
    assert "scripts/*.env.bak*" in patterns
    assert "*.env.bak*" in patterns
    assert "*.env" in patterns
    assert ".env" in patterns
    assert ".env.*" in patterns
    assert "*.pem" in patterns
    assert "*.key" in patterns
    assert "id_rsa" in patterns
    assert "*credentials*.json" in patterns

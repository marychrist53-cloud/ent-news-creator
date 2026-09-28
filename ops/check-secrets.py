"""Scan staged and non-ignored project files for common credential formats."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "Telegram bot token": re.compile(rb"\b[0-9]{7,12}:[A-Za-z0-9_-]{30,}\b"),
    "Google API key": re.compile(rb"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "OpenAI API key": re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(
        rb"\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"
    ),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def main() -> int:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        print("Run this check inside the project Git repository.", file=sys.stderr)
        return 2

    findings = []
    for name in result.stdout.splitlines():
        path = Path(name)
        if not path.is_file():
            continue
        try:
            content = path.read_bytes()
        except OSError:
            continue
        if b"\0" in content:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append((name, label))
    if findings:
        for name, label in findings:
            print(f"Possible {label}: {name}")
        return 1
    print("No common credential patterns found in Git files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail if any staged file contains a secret value from .env. Prints file names only, never values.

Run after `git add` and before `git commit`:  python3 -I scripts/check_secrets.py
Looks for .env at the repo root, then in the main checkout when run from a git worktree.
"""

import subprocess
import sys
from pathlib import Path

NON_SECRET_SUFFIXES = ("_PROFILE", "_URL", "_MODE")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def find_env() -> Path | None:
    top = Path(git("rev-parse", "--show-toplevel"))
    main_checkout = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir")).parent
    for candidate in (top / ".env", main_checkout / ".env"):
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    env = find_env()
    if env is None:
        print("check_secrets: no .env found; nothing to check")
        return 0
    pairs = [line.split("=", 1) for line in env.read_text().splitlines() if "=" in line]
    # Non-secret configuration (profile names, URLs, modes) can legitimately appear in docs and paths.
    secrets = {k.strip(): v.strip() for k, v in pairs if len(v.strip()) >= 12 and not k.strip().endswith(NON_SECRET_SUFFIXES)}
    staged = [f for f in git("diff", "--cached", "--name-only", "-z").split("\0") if f]
    leaks = []
    for name in staged:
        blob = subprocess.run(["git", "show", f":{name}"], capture_output=True).stdout
        hits = [k for k, v in secrets.items() if v.encode() in blob]
        if hits:
            leaks.append(f"{name} (value of {', '.join(hits)})")
    if leaks:
        print("check_secrets: SECRET VALUE FOUND in staged files:", ", ".join(leaks))
        return 1
    print(f"check_secrets: clean ({len(staged)} staged files, {len(secrets)} secrets checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

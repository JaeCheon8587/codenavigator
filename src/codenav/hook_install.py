"""Install/append a git pre-commit hook that runs `codenav frontmatter check --staged`.

Idempotent via sentinel markers — safe to invoke twice; safe to coexist with
pre-existing hook content from other tools.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

_SENTINEL_START = "# codenav-frontmatter-hook-start"
_SENTINEL_END = "# codenav-frontmatter-hook-end"

HOOK_BLOCK = f"""{_SENTINEL_START}
# codenav frontmatter validation. AI-free by default, fast, deterministic.
# Opt-in AI auto-fill: set env `CODENAV_HOOK_AUTOFILL=1` or git config `codenav.autofill true`.
# Bypass with: git commit --no-verify
codenav_exe=""
if [ -x "./codenav.ps1" ]; then codenav_exe="./codenav.ps1"
elif command -v codenav >/dev/null 2>&1; then codenav_exe="codenav"
fi
if [ -n "$codenav_exe" ]; then
  staged_cs=$(git diff --cached --name-only --diff-filter=ACM | grep '\\.cs$' || true)
  if [ -n "$staged_cs" ]; then
    "$codenav_exe" frontmatter check --staged
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "[codenav] frontmatter check failed. Fix issues or use 'git commit --no-verify' to bypass."
      exit $rc
    fi
    autofill="${{CODENAV_HOOK_AUTOFILL:-}}"
    if [ -z "$autofill" ]; then
      autofill=$(git config --get codenav.autofill 2>/dev/null || true)
    fi
    case "$autofill" in
      1|true|yes|on)
        echo "[codenav] autofill: running frontmatter gen on staged .cs..."
        if "$codenav_exe" frontmatter gen --staged --apply --allow-dirty; then
          echo "$staged_cs" | xargs git add 2>/dev/null || true
        else
          echo "[codenav] autofill failed; commit will proceed with current content"
        fi
        ;;
    esac
  fi
fi
{_SENTINEL_END}
"""


def _git_dir(root: Path) -> Path:
    """Resolve .git location — handles both repo and worktree (.git as file)."""
    gd = root / ".git"
    if gd.is_dir():
        return gd
    if gd.is_file():
        text = gd.read_text(encoding="utf-8", errors="replace").strip()
        if text.startswith("gitdir:"):
            ref = text.split("gitdir:", 1)[1].strip()
            p = (root / ref).resolve() if not Path(ref).is_absolute() else Path(ref)
            return p
    raise RuntimeError(f"not a git repo: {root}")


def install(root: Path, *, force: bool = False) -> str:
    """Return one of: 'created', 'appended', 'replaced', 'skipped-already-installed'."""
    git_dir = _git_dir(root)
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    if not hook_path.exists():
        content = "#!/usr/bin/env bash\nset -e\n\n" + HOOK_BLOCK
        hook_path.write_text(content, encoding="utf-8", newline="\n")
        _chmod_executable(hook_path)
        return "created"

    existing = hook_path.read_text(encoding="utf-8", errors="replace")
    if _SENTINEL_START in existing and _SENTINEL_END in existing:
        if not force:
            return "skipped-already-installed"
        # Force-replace existing block.
        before, _, rest = existing.partition(_SENTINEL_START)
        _, _, after = rest.partition(_SENTINEL_END)
        new_content = before.rstrip() + "\n\n" + HOOK_BLOCK + after.lstrip("\n")
        hook_path.write_text(new_content, encoding="utf-8", newline="\n")
        _chmod_executable(hook_path)
        return "replaced"

    # Append codenav block to existing pre-commit.
    if not existing.endswith("\n"):
        existing += "\n"
    new_content = existing + "\n" + HOOK_BLOCK
    hook_path.write_text(new_content, encoding="utf-8", newline="\n")
    _chmod_executable(hook_path)
    return "appended"


def uninstall(root: Path) -> str:
    """Return 'removed' | 'not-installed' | 'no-hook'."""
    git_dir = _git_dir(root)
    hook_path = git_dir / "hooks" / "pre-commit"
    if not hook_path.exists():
        return "no-hook"
    existing = hook_path.read_text(encoding="utf-8", errors="replace")
    if _SENTINEL_START not in existing:
        return "not-installed"
    before, _, rest = existing.partition(_SENTINEL_START)
    _, _, after = rest.partition(_SENTINEL_END)
    remainder = (before.rstrip() + "\n" + after.lstrip("\n")).strip()
    if not remainder or remainder == "#!/usr/bin/env bash\nset -e":
        hook_path.unlink()
        return "removed"
    hook_path.write_text(remainder + "\n", encoding="utf-8", newline="\n")
    return "removed"


def _chmod_executable(path: Path) -> None:
    try:
        st = path.stat()
        path.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass  # Windows

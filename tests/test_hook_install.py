"""Tests for codenav.hook_install — git pre-commit hook installer."""

import subprocess
from pathlib import Path

import pytest

from codenav import hook_install


@pytest.fixture
def tmp_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def test_install_creates_new_hook(tmp_repo):
    status = hook_install.install(tmp_repo)
    assert status == "created"
    hook = tmp_repo / ".git" / "hooks" / "pre-commit"
    body = hook.read_text(encoding="utf-8")
    assert "#!/usr/bin/env bash" in body
    assert "codenav-frontmatter-hook-start" in body
    assert "codenav-frontmatter-hook-end" in body
    assert "frontmatter check --staged" in body


def test_install_idempotent(tmp_repo):
    hook_install.install(tmp_repo)
    status = hook_install.install(tmp_repo)
    assert status == "skipped-already-installed"


def test_install_appends_to_existing_hook(tmp_repo):
    hook = tmp_repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/usr/bin/env bash\necho 'pre-existing'\n", encoding="utf-8")

    status = hook_install.install(tmp_repo)
    assert status == "appended"
    body = hook.read_text(encoding="utf-8")
    assert "pre-existing" in body
    assert "codenav-frontmatter-hook-start" in body


def test_install_force_replaces_existing_block(tmp_repo):
    hook_install.install(tmp_repo)
    hook = tmp_repo / ".git" / "hooks" / "pre-commit"

    body_before = hook.read_text(encoding="utf-8")
    # Re-write with --force; block should be replaced once (still single block).
    status = hook_install.install(tmp_repo, force=True)
    assert status == "replaced"
    body_after = hook.read_text(encoding="utf-8")
    assert body_after.count("codenav-frontmatter-hook-start") == 1


def test_uninstall_removes_block_keeps_other_content(tmp_repo):
    hook = tmp_repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/usr/bin/env bash\necho 'other tool'\n", encoding="utf-8")
    hook_install.install(tmp_repo)

    status = hook_install.uninstall(tmp_repo)
    assert status == "removed"
    body = hook.read_text(encoding="utf-8")
    assert "other tool" in body
    assert "codenav-frontmatter-hook-start" not in body


def test_uninstall_removes_file_when_only_codenav_block(tmp_repo):
    hook_install.install(tmp_repo)
    hook = tmp_repo / ".git" / "hooks" / "pre-commit"
    status = hook_install.uninstall(tmp_repo)
    assert status == "removed"
    assert not hook.exists()


def test_uninstall_not_installed_returns_status(tmp_repo):
    hook = tmp_repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/usr/bin/env bash\necho 'foo'\n", encoding="utf-8")
    status = hook_install.uninstall(tmp_repo)
    assert status == "not-installed"


def test_uninstall_no_hook_file(tmp_repo):
    status = hook_install.uninstall(tmp_repo)
    assert status == "no-hook"


def test_install_raises_on_non_git_dir(tmp_path):
    with pytest.raises(RuntimeError):
        hook_install.install(tmp_path)

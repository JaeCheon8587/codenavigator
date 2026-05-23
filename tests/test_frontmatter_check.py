"""Tests for codenav.frontmatter_check — static validation, no AI."""

import subprocess
import textwrap
from pathlib import Path

import pytest

from codenav import frontmatter_check


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return tmp_path


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def test_check_class_without_frontmatter_is_warn(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            public class Bare { }
        }
        """)
    issues = frontmatter_check.check_file(f)
    assert len(issues) == 1
    assert issues[0].level == "WARN"
    assert issues[0].class_name == "Bare"


def test_check_class_with_frontmatter_no_issue(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            // ---
            // description: has fm
            // ---
            public class WithFm { }
        }
        """)
    issues = frontmatter_check.check_file(f)
    assert issues == []


def test_check_class_with_xml_doc_no_issue(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            /// <summary>doc</summary>
            public class Doc { }
        }
        """)
    issues = frontmatter_check.check_file(f)
    assert issues == []


def test_check_empty_description_is_fail(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            // ---
            // description:
            // ---
            public class Empty { }
        }
        """)
    issues = frontmatter_check.check_file(f)
    fails = [i for i in issues if i.level == "FAIL"]
    assert len(fails) == 1
    assert "empty `description:`" in fails[0].message


def test_check_unterminated_block_is_fail(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            // ---
            // description: never closed
            public class Bad { }
        }
        """)
    issues = frontmatter_check.check_file(f)
    fails = [i for i in issues if i.level == "FAIL"]
    assert any("unterminated" in i.message for i in fails)


def test_check_malformed_tags_is_fail(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            // ---
            // description: ok
            // tags: not a list
            // ---
            public class Bad { }
        }
        """)
    issues = frontmatter_check.check_file(f)
    fails = [i for i in issues if i.level == "FAIL"]
    assert any("malformed `tags:`" in i.message for i in fails)


def test_check_empty_tags_list_ok(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            // ---
            // description: ok
            // tags: []
            // ---
            public class Good { }
        }
        """)
    issues = frontmatter_check.check_file(f)
    assert issues == []


def test_run_returns_zero_on_only_warn(tmp_repo):
    _write(tmp_repo / "a.cs", """
        namespace N {
            public class A { }
        }
""")
    _, code = frontmatter_check.run(tmp_repo, files=["a.cs"], strict=False)
    assert code == 0


def test_run_returns_one_on_fail(tmp_repo):
    _write(tmp_repo / "a.cs", """
        namespace N {
            // ---
            // description:
            // ---
            public class A { }
        }
        """)
    _, code = frontmatter_check.run(tmp_repo, files=["a.cs"], strict=False)
    assert code == 1


def test_run_strict_returns_one_on_warn(tmp_repo):
    _write(tmp_repo / "a.cs", """
        namespace N {
            public class A { }
        }
""")
    _, code = frontmatter_check.run(tmp_repo, files=["a.cs"], strict=True)
    assert code == 1


def test_run_staged_uses_git_index(tmp_repo):
    f = _write(tmp_repo / "a.cs", """
        namespace N {
            public class A { }
        }
""")
    subprocess.run(["git", "add", str(f)], cwd=tmp_repo, check=True)
    issues, code = frontmatter_check.run(tmp_repo, staged=True)
    assert len(issues) == 1
    assert issues[0].class_name == "A"
    assert code == 0  # WARN only


def test_run_staged_excludes_unstaged_files(tmp_repo):
    _write(tmp_repo / "staged.cs", """
        namespace N {
            public class S { }
        }
        """)
    _write(tmp_repo / "unstaged.cs", """
        namespace N {
            public class U { }
        }
        """)
    subprocess.run(["git", "add", "staged.cs"], cwd=tmp_repo, check=True)
    issues, _ = frontmatter_check.run(tmp_repo, staged=True)
    names = {i.class_name for i in issues}
    assert names == {"S"}

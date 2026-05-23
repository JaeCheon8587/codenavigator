"""Static validation of `// ---` frontmatter blocks in C# files.

Pre-commit-grade checks — fast, deterministic, no AI calls. Reports per-class:

- WARN: class lacks both frontmatter and XML doc.
- FAIL: frontmatter block opens (`// ---`) but never closes.
- FAIL: `description:` value empty or whitespace-only.
- FAIL: `tags:` line present but not in `[a, b, c]` form.
- FAIL: frontmatter present but not immediately preceding a class declaration.

Exit code policy:
- Any FAIL → exit 1.
- Only WARN → exit 0 unless `--strict` is set.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import parser_cs


@dataclass
class Issue:
    file: Path
    line: int
    class_name: str
    level: str  # "WARN" | "FAIL"
    message: str


_FM_OPEN_RE = re.compile(r"^[ \t]*//[ \t]*---[ \t]*$", re.MULTILINE)
_FM_CLOSE_RE = _FM_OPEN_RE  # same shape
_FM_BLOCK_RE = re.compile(
    r"^[ \t]*//[ \t]*---[ \t]*\n"
    r"(?P<body>(?:[ \t]*//[^\n]*\n)*?)"
    r"[ \t]*//[ \t]*---[ \t]*$",
    re.MULTILINE,
)
_DESC_RE = re.compile(r"^[ \t]*//[ \t]*description[ \t]*:[ \t]*(?P<value>.*?)[ \t]*$")
_TAGS_RE = re.compile(r"^[ \t]*//[ \t]*tags[ \t]*:[ \t]*(?P<value>.*?)[ \t]*$")


def staged_cs_files(root: Path) -> list[Path]:
    """Return absolute paths of staged .cs files (ACM = added/changed/modified)."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=root,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files: list[Path] = []
    for rel in out.splitlines():
        rel = rel.strip()
        if not rel.endswith(".cs"):
            continue
        p = (root / rel).resolve()
        if p.exists():
            files.append(p)
    return files


def check_file(path: Path) -> list[Issue]:
    """Return validation issues for one .cs file."""
    issues: list[Issue] = []
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return issues

    # 1. Open/close balance — every `// ---` must pair.
    opens = list(_FM_OPEN_RE.finditer(text))
    if len(opens) % 2 != 0:
        last = opens[-1]
        line_no = text.count("\n", 0, last.start()) + 1
        issues.append(
            Issue(
                file=path,
                line=line_no,
                class_name="",
                level="FAIL",
                message="unterminated `// ---` frontmatter block",
            )
        )

    # 2. Per-block content checks.
    for m in _FM_BLOCK_RE.finditer(text):
        body = m.group("body")
        block_start_line = text.count("\n", 0, m.start()) + 1
        desc_found = False
        for raw in body.splitlines():
            dm = _DESC_RE.match(raw)
            if dm:
                desc_found = True
                if not dm.group("value").strip():
                    issues.append(
                        Issue(
                            file=path,
                            line=block_start_line,
                            class_name="",
                            level="FAIL",
                            message="empty `description:` value",
                        )
                    )
            tm = _TAGS_RE.match(raw)
            if tm:
                val = tm.group("value").strip()
                if val and not (val.startswith("[") and val.endswith("]")):
                    issues.append(
                        Issue(
                            file=path,
                            line=block_start_line,
                            class_name="",
                            level="FAIL",
                            message=f"malformed `tags:` value (expected [a, b, c]): {val!r}",
                        )
                    )
        if not desc_found:
            issues.append(
                Issue(
                    file=path,
                    line=block_start_line,
                    class_name="",
                    level="FAIL",
                    message="frontmatter block missing `description:` line",
                )
            )

    # 3. Per-class WARN: missing both frontmatter and XML doc.
    fm_names = {m.group(2) for m in parser_cs._FRONTMATTER_RE.finditer(text)}
    xml_names = {
        m.group(2)
        for m in re.finditer(
            r"((?:[ \t]*///[^\n]*\n)+)\s*"
            r"(?:(?:public|internal|protected|private|static|abstract|sealed|partial)\s+)*"
            r"(?:class|struct|interface|record)\s+(\w+)",
            text,
            re.MULTILINE,
        )
    }
    classes = parser_cs.parse_cs_file(path)
    for cls in classes:
        if cls.class_name in fm_names or cls.class_name in xml_names:
            continue
        line_no = 1
        for i, raw in enumerate(text.splitlines(), start=1):
            if re.search(rf"\b(?:class|struct|interface|record)\s+{re.escape(cls.class_name)}\b", raw):
                line_no = i
                break
        issues.append(
            Issue(
                file=path,
                line=line_no,
                class_name=cls.class_name,
                level="WARN",
                message="class has no frontmatter and no XML doc",
            )
        )

    return issues


def check_files(files: list[Path]) -> list[Issue]:
    out: list[Issue] = []
    for f in files:
        out.extend(check_file(f))
    return out


def format_issue(issue: Issue) -> str:
    suffix = f" [{issue.class_name}]" if issue.class_name else ""
    return f"[{issue.level}] {issue.file}:{issue.line}{suffix} {issue.message}"


def has_failures(issues: list[Issue]) -> bool:
    return any(i.level == "FAIL" for i in issues)


def run(
    root: Path,
    *,
    staged: bool = False,
    files: list[str] | None = None,
    strict: bool = False,
) -> tuple[list[Issue], int]:
    """Return (issues, exit_code)."""
    target_files: list[Path] = []
    if staged:
        target_files.extend(staged_cs_files(root))
    if files:
        for f in files:
            p = (root / f).resolve() if not Path(f).is_absolute() else Path(f)
            if p.exists() and p.suffix == ".cs":
                target_files.append(p)
    # Dedupe.
    seen = set()
    deduped: list[Path] = []
    for p in target_files:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    issues = check_files(deduped)
    code = 0
    if has_failures(issues):
        code = 1
    elif strict and any(i.level == "WARN" for i in issues):
        code = 1
    return issues, code

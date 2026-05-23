"""codenav CLI entry point."""

import argparse
import json
import sys
from pathlib import Path

from codenav import services, app as web_app, frontmatter_gen, frontmatter_check, hook_install


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    stats = services.get_status(root)
    print(f"DB      : {stats['db_path']}")
    print(f"Classes : {stats['total_classes']}")
    print(f"Manual  : {stats['manual_classes']}")
    print(f"Stale   : {stats['stale_classes']}")
    print(f"LastIdx : {stats['last_indexed'] or 'never'}")
    if stats["stale_files"]:
        print("Stale files:")
        for file in stats["stale_files"]:
            print(f"  {file}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    try:
        results = services.search_index(
            root,
            args.query,
            limit=args.limit,
            solution=args.solution or None,
            project=args.project or None,
            scope=args.scope,
        )
    except Exception:
        print("No index. Run: codenav reindex --full", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if not results:
        print("No results.")
        return 0
    for result in results:
        stale_mark = " [stale]" if result.get("stale") else ""
        print(f"[{result['score']:.2f}]{stale_mark} {result['project'] or result['solution']} / {result['namespace']} / {result['class']}")
        print(f"       {services.display_path(root, result['file'])}")
        print(f"       {result['description']}")
        print(f"       tags: {', '.join(result['tags'])}")
        if args.scope == "method" and result.get("methods"):
            for method in result["methods"][:5]:
                print(f"         • {method['name']}: {method.get('description', '')}")
        print()
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    result = services.run_reindex(
        root,
        full=args.full,
        files=args.files,
        changed=args.changed,
        verbose=args.verbose,
        no_ai=args.no_ai,
    )
    if result.get("deleted_count") and args.verbose:
        print(f"  [DELETE] removed {result['deleted_count']} classes from deleted files", file=sys.stderr)
    print(result["message"], file=sys.stderr)
    if result.get("error"):
        print(result["error"], file=sys.stderr)
    return int(result["code"])


def cmd_delete(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    result = services.delete_file_index(root, args.file, confirm=args.yes)
    if result.get("deleted", 0) == 0 and result.get("would_delete", 0) == 0:
        if args.json:
            print(json.dumps(result))
        else:
            print(f"No indexed classes for file: {result['file']}")
        return 0
    if not args.yes:
        if args.json:
            print(json.dumps(result))
        else:
            print(f"[dry-run] Would delete {result['would_delete']} class(es) for {result['file']}. Re-run with --yes to confirm.")
        return 0
    if args.json:
        print(json.dumps(result))
    else:
        print(f"Deleted {result['deleted']} class(es) for {result['file']}")
    return 0


def cmd_frontmatter_gen(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    projects: list[str] | None = None
    if getattr(args, "projects", None):
        projects = [p.strip() for p in args.projects.split(",") if p.strip()]
        if not projects:
            projects = None
    try:
        result = frontmatter_gen.run(
            root,
            limit=args.limit,
            apply=args.apply,
            allow_dirty=args.allow_dirty,
            verbose=args.verbose,
            projects=projects,
        )
    except RuntimeError as exc:
        print(f"[codenav] {exc}", file=sys.stderr)
        return 1
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(
        f"[{mode}] scanned_files={result.scanned_files} candidates={result.candidates} "
        f"generated={result.generated} written={result.written} "
        f"failures={len(result.failures)} skipped_files={len(result.skipped_files)}",
        file=sys.stderr,
    )
    if result.failures and args.verbose:
        for fail in result.failures:
            print(f"  [FAIL] {fail}", file=sys.stderr)
    if result.skipped_files and args.verbose:
        for skip in result.skipped_files:
            print(f"  [SKIP] {skip}", file=sys.stderr)
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    web_app.run_ui_server(root, host=args.host, port=args.port)
    return 0


def cmd_frontmatter_check(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    issues, code = frontmatter_check.run(
        root,
        staged=args.staged,
        files=args.files,
        strict=args.strict,
    )
    fails = [i for i in issues if i.level == "FAIL"]
    warns = [i for i in issues if i.level == "WARN"]
    for i in issues:
        print(frontmatter_check.format_issue(i), file=sys.stderr)
    print(
        f"[check] files={len({i.file for i in issues})} warn={len(warns)} fail={len(fails)}",
        file=sys.stderr,
    )
    return code


def cmd_install_hook(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path.cwd()
    try:
        if args.uninstall:
            status = hook_install.uninstall(root)
        else:
            status = hook_install.install(root, force=args.force)
    except RuntimeError as exc:
        print(f"[codenav] {exc}", file=sys.stderr)
        return 1
    print(f"[install-hook] {status}", file=sys.stderr)
    return 0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="codenav", description="CodeNavigator CLI")
    parser.add_argument("--root", default="", help="Repo root (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show index stats")

    sp = sub.add_parser("search", help="Search classes by keyword")
    sp.add_argument("query", help="Keyword query (e.g. '데이터 수집')")
    sp.add_argument("--limit", type=int, default=30, help="Max results (default: 30, 0 = unlimited)")
    sp.add_argument("--scope", choices=["class", "method"], default="class")
    sp.add_argument("--solution", default="")
    sp.add_argument("--project", default="")
    sp.add_argument("--json", action="store_true", help="Output as JSON array")

    rp = sub.add_parser("reindex", help="Index / update class descriptions")
    rp.add_argument("--full", action="store_true", help="Reindex entire repo")
    rp.add_argument("--files", nargs="+", metavar="FILE", help="Specific files")
    rp.add_argument("--changed", action="store_true", help="Staged .cs files (git diff --cached)")
    rp.add_argument("--no-ai", action="store_true", help="Skip AI enrichment (parser/frontmatter only, no stale marking)")
    rp.add_argument("--verbose", action="store_true")

    dp = sub.add_parser("delete", help="Delete indexed classes for a file")
    dp.add_argument("--file", required=True, help="C# file path (absolute or relative to --root)")
    dp.add_argument("--yes", action="store_true", help="Actually delete (default: dry-run)")
    dp.add_argument("--json", action="store_true", help="Output as JSON")

    up = sub.add_parser("ui", help="Run local web UI")
    up.add_argument("--host", default="127.0.0.1")
    up.add_argument("--port", type=int, default=8765)

    fp = sub.add_parser("frontmatter", help="Frontmatter operations")
    fp_sub = fp.add_subparsers(dest="fm_cmd", required=True)
    fp_gen = fp_sub.add_parser("gen", help="AI-generate `// ---` blocks for classes lacking description")
    fp_gen.add_argument("--limit", type=int, default=0, help="Max classes per invocation (default: 0 = unlimited)")
    fp_gen.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    fp_gen.add_argument("--allow-dirty", action="store_true", help="Run even if git working tree is dirty")
    fp_gen.add_argument(
        "--projects",
        metavar="CSV",
        help="Comma-separated .csproj filenames to scope frontmatter generation (e.g. 'Foo.csproj,Bar.csproj'). Only .cs under matching csproj folders are considered.",
    )
    fp_gen.add_argument("--verbose", action="store_true")

    fp_check = fp_sub.add_parser("check", help="Validate `// ---` frontmatter syntax (no AI)")
    fp_check.add_argument("--staged", action="store_true", help="Validate git-staged .cs files")
    fp_check.add_argument("--files", nargs="+", metavar="FILE", help="Explicit file list")
    fp_check.add_argument("--strict", action="store_true", help="Exit 1 on WARN too (default: only FAIL)")

    fp_hook = fp_sub.add_parser("install-hook", help="Install/append pre-commit hook for frontmatter check")
    fp_hook.add_argument("--force", action="store_true", help="Replace existing codenav hook block")
    fp_hook.add_argument("--uninstall", action="store_true", help="Remove codenav hook block")

    args = parser.parse_args()
    if args.cmd == "frontmatter":
        if args.fm_cmd == "gen":
            sys.exit(cmd_frontmatter_gen(args))
        if args.fm_cmd == "check":
            sys.exit(cmd_frontmatter_check(args))
        if args.fm_cmd == "install-hook":
            sys.exit(cmd_install_hook(args))
        parser.error(f"unknown frontmatter subcommand: {args.fm_cmd}")
    dispatch = {
        "status": cmd_status,
        "search": cmd_search,
        "reindex": cmd_reindex,
        "delete": cmd_delete,
        "ui": cmd_ui,
    }
    sys.exit(dispatch[args.cmd](args))


if __name__ == "__main__":
    main()

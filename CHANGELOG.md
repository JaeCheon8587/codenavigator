# Changelog

## v1.0.5 — 2026-05-23

- feat(frontmatter): `codenav frontmatter check` — AI-free static validation. Flags missing frontmatter (WARN), empty description, malformed `tags:`, unterminated `// ---` blocks (FAIL). Supports `--staged` (git index), `--files`, `--strict` (exit 1 on WARN).
- feat(frontmatter): `codenav frontmatter install-hook` — installs/appends `.git/hooks/pre-commit` block that runs `frontmatter check --staged`. Idempotent via sentinel markers. Coexists with other pre-commit content. `--uninstall` removes the block; `--force` replaces. Bypass at commit time with `git commit --no-verify`.
- 21 new pytest cases.

## v1.0.4 — 2026-05-23

- change(frontmatter-gen): `--limit` default is now `0` = unlimited (was `50`). Cap classes per invocation only when user explicitly passes `--limit N`. 2 new pytest cases.

## v1.0.3 — 2026-05-23

- feat(frontmatter-gen): `--projects` CSV flag scopes generation to specified `.csproj` projects. Matches `.csproj` filenames case-insensitively across the repo via rglob; only `.cs` under matching csproj folders become candidates. Missing csproj names are warned on stderr. Suffix `.csproj` optional in input. 4 new pytest cases.

## v1.0.2 — 2026-05-23

- fix(tests): use `pathlib.Path` to build expected relative file path in `test_dashboard_shows_relative_file_path` so Linux CI (forward slash) and Windows local (backslash) both pass. v1.0.1 publish workflow blocked on this single assertion.

## v1.0.1 — 2026-05-23

- README: per-project venv install pattern documented (`Tools/codenavigator/` layout + `codenav.ps1` launcher).
- No code changes.

## v1.0.0 — 2026-05-22

First independent release. Split out of the `Claudecode-For-Me` monorepo into a standalone Python package on PyPI.

### Features

- C# regex parser extracts `class` / `struct` / `interface` / `record` plus method names.
- SQLite FTS5 index with bm25 ranking + tag-hit bonus + CJK bigram tokenization.
- PascalCase auto-split in queries (`DataCollector` → `data` / `collector`).
- In-source `// ---` frontmatter blocks as description/tags source.
- `codenav reindex --no-ai` bootstrap mode (parser-only, no Claude calls).
- `codenav frontmatter gen` — AI-driven frontmatter generator with dry-run / `--apply` safety.
- `codenav search` default limit 30, `--limit 0` for unlimited.
- `codenav ui` — local web dashboard for editing descriptions and tags.
- `.codenavignore` — gitignore-style exclusion file.
- Stale rows with non-empty description remain searchable (marked `[stale]`).

### Notes

- Distributed as PyPI package `codenavigator`. Install: `pip install codenavigator`. CLI: `codenav`.
- Built and published via GitHub Actions on tag `v*` push (trusted publishing).
- 71 pytest cases (parser, services, search, app, indexer, store, frontmatter_gen).

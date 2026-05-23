# Changelog

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

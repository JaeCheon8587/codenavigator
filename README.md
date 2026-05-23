# codenavigator

> AI coding-agent tool: SQLite FTS5 semantic class index for C# codebases.

Natural-language keyword search across C# `class` / `struct` / `interface` / `record` declarations. Parser-only baseline + optional AI enrichment via Claude Code CLI. Local web dashboard for browsing and editing metadata. Designed to slot in as a tool for AI coding agents (Claude Code, Cursor, etc.) to shortlist candidate files before deep reads.

## Install

### Global (simple)

```bash
pip install codenavigator
```

Registers a `codenav` CLI on PATH. Python 3.11+.

### Per-project venv (isolated, recommended for projects with their own `Tools/` layout)

```bash
cd <your-project>
python -m venv Tools/codenavigator
Tools/codenavigator/Scripts/pip install codenavigator   # Windows
# Tools/codenavigator/bin/pip install codenavigator     # Unix

# Optional launcher at project root (PowerShell):
#   codenav.ps1
#     & "$PSScriptRoot\Tools\codenavigator\Scripts\codenav.exe" @Args
```

Add to `.gitignore`:

```
Tools/codenavigator/
```

This keeps the venv (binary + dependencies) out of git while letting the launcher script ship with the repo.

## Quickstart

```bash
cd <your-csharp-repo>

# 1) Parser-only baseline index (no AI calls, no .cs file changes)
codenav reindex --full --no-ai

# 2) Search
codenav search "주문 처리"
codenav search "DataCollector" --limit 30

# 3) Optional: AI fills in descriptions by inserting `// ---` frontmatter blocks
codenav frontmatter gen --limit 30 --apply   # requires `claude` CLI on PATH

# 4) Re-index to pick up the new frontmatter
codenav reindex --full --no-ai

# 5) Local web UI
codenav ui --port 9876
```

## Frontmatter convention

To give a C# class a human-authored description, place a YAML-style comment block directly above its declaration:

```csharp
// ---
// description: 은행 계좌 도메인 엔티티
// tags: [account, banking, domain]
// ---
public class Account { ... }
```

- `description`: single-line string.
- `tags`: inline sequence; comma-separated.
- An existing `/// <summary>` XML doc takes precedence.

Full spec: [`docs/frontmatter.md`](docs/frontmatter.md).

## Commands

| Command | Description |
|---|---|
| `codenav reindex --full [--no-ai]` | Rebuild the whole index. `--no-ai` skips Claude enrichment. |
| `codenav reindex --files <path>...` | Re-index specific files (paths relative to `--root` or absolute). |
| `codenav reindex --changed` | Index git-staged `.cs` files only. |
| `codenav search <query> [--limit N]` | FTS5 + tag-hit bonus search (default 30, `--limit 0` = unlimited). |
| `codenav frontmatter gen [--apply]` | AI-driven `// ---` block insertion (dry-run by default). |
| `codenav status` | Index statistics. |
| `codenav delete --file <path> --yes` | Remove indexed entries for a single file. |
| `codenav ui --port <N>` | Launch the local web dashboard. |

`--root <path>` selects the repo root (default: cwd). The SQLite DB lives at `<root>/.codenav/index.sqlite`.

## `.codenavignore`

gitignore-style file at the repo root. Supports:

```
# tree prefix
tools/

# glob anywhere
*AutoGen*

# bare name (any path segment)
GeneratedFiles
```

## Search ranking

- FTS5 `bm25` over class_name, namespace, description, tags, bigram (column weights 3.0 / 2.0 / 1.0 / 2.0 / 1.5).
- `+2.0` bonus per exact tag hit.
- PascalCase auto-split (`DataCollector` → `data`, `collector`).
- CJK bigram tokenization for Korean / Chinese / Japanese (`"문서처리"` → `["문서", "서처", "처리"]`).
- `stale=1` rows surface in results only if their `description` is non-empty (marked `[stale]`).

## Pre-commit hook

Automatic incremental indexing of staged `.cs` files:

```bash
# from your repo root
bash <(curl -s https://raw.githubusercontent.com/JaeCheon8587/codenavigator/main/install-hook.sh)
# or PowerShell
iwr -useb https://raw.githubusercontent.com/JaeCheon8587/codenavigator/main/install-hook.ps1 | iex
```

Installs a Git pre-commit hook calling `codenav reindex --changed`.

## Use with Claude Code

If you also use the [`claudecode-for-me`](https://github.com/JaeCheon8587/Claudecode-For-Me) Claude Code plugin, two slash commands wrap `codenav`:

- `/claudecode-for-me:codenav-bootstrap` → `codenav reindex --full --no-ai`.
- `/claudecode-for-me:codenav-frontmatter-gen` → `codenav frontmatter gen` with dry-run / apply safety.

Both delegate to the `codenav` CLI on PATH. The plugin does not bundle the tool — `pip install codenavigator` is the single source.

## License

MIT

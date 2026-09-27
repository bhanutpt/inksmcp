# inksmcp

An MCP (Model Context Protocol) server that lets AI assistants drive **Inkscape**: create, inspect, edit and export vector graphics through high-level tools that do the fiddly maths for the agent.

> Status: **Phase 2 in progress** — `align`, `layout`, `connect` done (49 tests green against real Inkscape). See [docs/02-plan.md](docs/02-plan.md).

## Requirements

- Inkscape ≥ 1.0 (developed on 1.4.4). Found via PATH or `INKSCAPE_PATH`.
- [uv](https://docs.astral.sh/uv/)

## Run

```bash
uv sync
uv run pytest            # needs Inkscape installed
uv run inksmcp           # MCP server on stdio
```

### Register with Claude Code

This repo ships a project-level [`.mcp.json`](.mcp.json): open a Claude Code session in this folder and approve the `inkscape` server. To use it from any folder instead:

```bash
claude mcp add --scope user inkscape -- uv run --directory C:/drv/ai/inksmcp inksmcp
```

## Tools

`inkscape_info` · `document_create` · `document_open` · `document_save` · `inspect` · `add_elements` · `update_elements` · `delete_elements` · `align` · `layout` · `connect` · `path_operation` · `run_actions` · `export` · `render_preview` — details in [docs/04-features.md](docs/04-features.md).

## Documentation

| Doc | What it holds |
|---|---|
| [docs/README.md](docs/README.md) | Index, how we work, how the docs are maintained |
| [docs/01-objectives.md](docs/01-objectives.md) | Why this exists, goals, non-goals, success criteria |
| [docs/02-plan.md](docs/02-plan.md) | Phased roadmap and current phase |
| [docs/03-architecture.md](docs/03-architecture.md) | Layers and abstraction design |
| [docs/04-features.md](docs/04-features.md) | Feature/tool tracker (planned → done) |
| [docs/05-inkscape-notes.md](docs/05-inkscape-notes.md) | Inkscape facts proven by experiments |
| [docs/06-decisions.md](docs/06-decisions.md) | Decision log (what we chose and why) |
| [docs/07-lessons-learned.md](docs/07-lessons-learned.md) | What we learned the hard way |
| [experiments/](experiments/README.md) | The probes behind the findings |
| [CHANGELOG.md](CHANGELOG.md) | Dated record of changes |

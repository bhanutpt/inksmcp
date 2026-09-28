# Development handbook

How inksmcp is built, and where its history lives. For using it, see the [user docs](../README.md).

These are **living documents**: they grow with the code and are updated in the same commit.

## Files

| File | What it holds |
|---|---|
| [objectives.md](objectives.md) | Goals, non-goals, success criteria |
| [roadmap.md](roadmap.md) | Phases, the current phase, next steps |
| [architecture.md](architecture.md) | Layers, abstractions, data flow |
| [features.md](features.md) | Every tool and feature with its status, the agent load it removes, and its tests |
| [inkscape-notes.md](inkscape-notes.md) | Inkscape and SVG facts proven by experiments (F#, S#) |
| [decisions.md](decisions.md) | Decision log, ADR-lite (D-###) |
| [lessons-learned.md](lessons-learned.md) | Pitfalls and what we do about them now |
| [benchmarks.md](benchmarks.md) | Calls and tokens for reference tasks, per phase |
| [field-reports/](field-reports/README.md) | Reports from agent sessions that used the tools for real tasks |
| [releasing.md](releasing.md) | How a version goes out (PyPI, GitHub, MCP Registry) |

Also: [CHANGELOG.md](../../CHANGELOG.md) for dated changes, [experiments/](../../experiments/README.md) for the probes behind every finding.

## How we work (D-003)

Theory only at the level of principles; reality decides the details.

1. **Question**: something we need to rely on ("are export options sticky?").
2. **Experiment**: a small script in `experiments/eNN_*.py` against the real Inkscape.
3. **Finding**: recorded in `inkscape-notes.md` with an id (F#, S#) and its source.
4. **Test**: a test in `tests/` that fails if the finding stops being true or the code forgets it.
5. **Code**: the smallest abstraction that removes the burden from the agent.
6. **Real usage**: drive the server like an agent would (a field test, ideally by a fresh agent that sees only the tool descriptions); what the agent still has to compute becomes the next feature.

A surprising test failure is a new experiment result: record it, don't just patch it.

## Commands

```bash
uv sync                                   # dev environment
uv run pytest                             # needs Inkscape; ~30 s
uv run inksmcp                            # the server on stdio
uv run python experiments/e30_foreign_files.py
uv run python scripts/gen_tools_doc.py    # regenerate docs/tools.md after changing a tool
```

While an MCP client holds the server open, `uv run` can't replace `.venv/Scripts/inksmcp.exe` on Windows: use `uv run --no-sync` (see lessons learned).

## Maintenance rules

- **Every meaningful change updates the docs in the same commit.** Code without doc updates is incomplete.
- New feature → add or update a row in `features.md`; a changed tool signature or description → regenerate `docs/tools.md` (a test fails otherwise).
- A choice between alternatives → an entry in `decisions.md`.
- Something surprised us or cost time → `lessons-learned.md`.
- Discovered Inkscape behaviour → `inkscape-notes.md`.
- Phase progress → tick items in `roadmap.md`.
- User-visible change → `CHANGELOG.md` under `Unreleased`.
- A field report → a row in `field-reports/README.md`; each follow-up becomes experiment → test → fix, then is marked done there.
- Use absolute dates (`YYYY-MM-DD`), never "yesterday" or "last week".
- Placeholders are marked `TBD`: search for them to find gaps.

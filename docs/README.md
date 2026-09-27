# Docs index

These docs are **living documents**. They start as placeholders and grow as we build and learn.

## Files

1. [01-objectives.md](01-objectives.md) — goals, non-goals, success criteria
2. [02-plan.md](02-plan.md) — phased roadmap, current phase, next steps
3. [03-architecture.md](03-architecture.md) — layers, abstractions, data flow
4. [04-features.md](04-features.md) — MCP tools/resources/prompts and their status
5. [05-inkscape-notes.md](05-inkscape-notes.md) — Inkscape facts, CLI/actions, quirks
6. [06-decisions.md](06-decisions.md) — decision log (ADR-lite)
7. [07-lessons-learned.md](07-lessons-learned.md) — lessons, pitfalls, efficiency tips
8. [08-benchmarks.md](08-benchmarks.md) — calls and tokens for reference tasks, per phase

Also: [field-reports/](field-reports/README.md) from real agent sessions, [../CHANGELOG.md](../CHANGELOG.md) for dated changes, [../experiments/](../experiments/README.md) for the probes behind every finding.

## How we work (D-003)

Theory only at the level of principles; reality decides the details.

1. **Question** — something we need to rely on ("are export options sticky?").
2. **Experiment** — a small script in `experiments/eNN_*.py` against the real Inkscape.
3. **Finding** — recorded in `05-inkscape-notes.md` with an id (F#, S#) and its source.
4. **Test** — a test in `tests/` that fails if the finding stops being true or the code forgets it.
5. **Code** — the smallest abstraction that removes the burden from the agent.
6. **Real usage** — drive the server like an agent would; what the agent still has to compute becomes the next feature.

A surprising test failure is a new experiment result — record it, don't just patch it.

## Maintenance rules

- **Every meaningful change updates the docs in the same commit.** Code without doc updates is incomplete.
- New feature → add/update a row in `04-features.md`.
- A choice between alternatives → add an entry in `06-decisions.md`.
- Something surprised us or cost time → add it to `07-lessons-learned.md`.
- Discovered Inkscape behavior → `05-inkscape-notes.md`.
- Phase progress → tick items in `02-plan.md`.
- User-visible change → `CHANGELOG.md` under `Unreleased`.
- Use absolute dates (`YYYY-MM-DD`), never "yesterday" or "last week".
- Placeholders are marked `TBD` — search for them to find gaps.

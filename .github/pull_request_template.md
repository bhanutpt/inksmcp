## What this changes

<!-- What does the agent no longer have to compute, retry or work around? Link the issue or field report. -->

## Checklist

- [ ] Experiment in `experiments/` for any Inkscape behaviour relied on, finding in `docs/development/inkscape-notes.md`
- [ ] Tests added or updated; `uv run pytest` passes
- [ ] Docs in the same change: `features.md`, `CHANGELOG.md` (Unreleased), `decisions.md` if a choice was made
- [ ] `docs/tools.md` regenerated if a tool changed (`uv run python scripts/gen_tools_doc.py`)

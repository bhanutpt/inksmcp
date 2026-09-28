# inksmcp — notes for Claude

MCP server for Inkscape. Start by reading [docs/README.md](docs/README.md) and [docs/02-plan.md](docs/02-plan.md) for the current phase.

- Work experiment-first (see "How we work" in `docs/README.md`): prove Inkscape behaviour in `experiments/`, record it in `docs/05-inkscape-notes.md`, guard it with a test.
- Keep the docs living: follow the maintenance rules in `docs/README.md` and update docs in the same commit as code.
- Commands: `uv run pytest` (needs Inkscape, ~30 s), `uv run inksmcp` (stdio server), `uv run python experiments/eNN_x.py`.
- Inkscape CLI on this machine: `C:\Program Files\Inkscape\bin\inkscape.com` (use `.com`, not `.exe`).
- Use `uv run`, not system `pip`/`python` (they point at different interpreters). Don't write source files with PowerShell `Set-Content` (adds a BOM).
- Commit messages containing double quotes break PowerShell 5.1 argument passing: write the message to a file and use `git commit -F <file>`.
- Field tests: reports from separate agent sessions live in `docs/field-reports/`; turn each follow-up into experiment → test → fix, then mark it done in the table.

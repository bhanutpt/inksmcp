# inksmcp — notes for Claude

MCP server for Inkscape. Start by reading [docs/development/README.md](docs/development/README.md) and [docs/development/roadmap.md](docs/development/roadmap.md) for the current phase.

- Work experiment-first (see "How we work" in `docs/development/README.md`): prove Inkscape behaviour in `experiments/`, record it in `docs/development/inkscape-notes.md`, guard it with a test.
- Keep the docs living: follow the maintenance rules in `docs/development/README.md` and update docs in the same commit as code.
- Commands: `uv run pytest` (needs Inkscape, ~30 s), `uv run inksmcp` (stdio server), `uv run python experiments/eNN_x.py`.
- Inkscape CLI on this machine: `C:\Program Files\Inkscape\bin\inkscape.com` (use `.com`, not `.exe`).
- Use `uv run`, not system `pip`/`python` (they point at different interpreters). Don't write source files with PowerShell `Set-Content` (adds a BOM).
- Commit messages containing double quotes break PowerShell 5.1 argument passing: write the message to a file and use `git commit -F <file>`.
- Releases: `docs/development/releasing.md` (`scripts/bump_version.py X.Y.Z`, then tag). After changing a tool, run `uv run python scripts/gen_tools_doc.py` (a test checks `docs/tools.md`).
- Field tests: reports from separate agent sessions live in `docs/development/field-reports/`; turn each follow-up into experiment → test → fix, then mark it done in the table.

# Contributing to inksmcp

Thanks for helping. There are three kinds of contribution, and all of them are welcome.

## Field reports

The most useful thing you can send is a report from a real session: what you asked for, how many tool
calls it took, and what the agent had to compute by hand, retry or work around. Use the
[field report issue form](https://github.com/bhanutpt/inksmcp/issues/new?template=field_report.yml).
Reports drive the roadmap: the ones received so far are in
[docs/development/field-reports](docs/development/field-reports/README.md).

## Bug reports

Use the [bug report form](https://github.com/bhanutpt/inksmcp/issues/new?template=bug_report.yml).
Include the exact tool call, the full response (including any error text), and your Inkscape version
(`inkscape_info` reports it). If a file is involved and you can share it, attach it.

## Code

### Setup

```bash
git clone https://github.com/bhanutpt/inksmcp
cd inksmcp
uv sync
uv run pytest          # needs Inkscape installed; about 30 s
```

### How changes are made

The project is built experiment-first ([development handbook](docs/development/README.md)):

1. **Experiment.** Anything the code relies on about Inkscape's behaviour is first shown by a small
   script in `experiments/eNN_*.py`, run against the real Inkscape.
2. **Record.** The finding goes in `docs/development/inkscape-notes.md`. A choice between
   alternatives goes in `decisions.md`.
3. **Test.** A test in `tests/` fails if the finding stops being true or the code forgets it.
4. **Code.** Write the smallest abstraction that removes the work from the agent.
5. **Docs in the same commit.** Update `features.md`, `CHANGELOG.md` (under *Unreleased*), and
   `docs/tools.md` if a tool changed (`uv run python scripts/gen_tools_doc.py`; a test checks it).

### Guidelines

- **Tools describe intent, not SVG plumbing.** A new option on an existing tool is better than a new
  tool: every tool adds to the context each session pays for.
- **Every tool is all-or-nothing.** On an error, the document is restored and the message says so.
- **Responses are compact.** They return ids, boxes and warnings, not the document.
- **General-purpose.** Domain vocabularies (cartography, architecture, comic balloon styles) stay
  out of the core. Build them from the general primitives, or propose them as an optional module.
- **Match the surrounding code.** Keep its style, naming and comment density. Python 3.12+, run
  through `uv run`.

### Pull requests

Keep a PR to one change, and describe what it removes from the agent's work. Include the experiment
and the tests. CI runs the suite against Inkscape on Linux, Windows and macOS.

## Code of conduct

Be kind and constructive. Harassment or personal attacks aren't tolerated. Report problems to the
maintainer at the address in `pyproject.toml`.

# Objectives

## Vision

Give AI assistants a reliable, well-abstracted way to work with Inkscape: they describe *intent* ("add a rounded blue rectangle behind the title", "export page 2 as a 300 dpi PNG"), and the MCP server translates that into correct SVG/Inkscape operations.

## Goals

1. **Real abstraction** — tools expose design concepts (document, layer, shape, text, style, export), not raw CLI flags or XML plumbing.
2. **Safe and predictable** — operations are validated, reversible where possible, and never silently corrupt a document.
3. **Inspectable** — the AI can always ask "what is in this document?" and get a compact, structured answer.
4. **Visual feedback** — the AI can render a preview (PNG) to check its own work.
5. **Cross-platform ready** — developed on Windows first, but no Windows-only design assumptions in the core.
6. **Well documented and tested** — every tool has a description, examples, and tests.

## Non-goals (for now)

- Replacing Inkscape's GUI or live-controlling an open GUI window (may revisit later).
- Supporting Inkscape 0.92 or older.
- Raster image editing (that is GIMP territory).
- TBD

## Success criteria

- [ ] An assistant can create a simple poster/diagram from scratch using only MCP tools.
- [ ] An assistant can open an existing SVG, understand its structure, and make targeted edits.
- [ ] Export to PNG / PDF / plain SVG works reliably.
- [ ] Automated test suite runs green against the installed Inkscape.
- [ ] TBD

## Target users / clients

- Claude Code / Claude Desktop and any MCP-compatible client.
- TBD

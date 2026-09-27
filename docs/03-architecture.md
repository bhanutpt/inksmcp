# Architecture

As built in Phase 1 (see D-004). Layers only depend downwards.

```
┌───────────────────────────────────────────────────────────┐
│ server.py   MCP layer — thin tool wrappers, Session       │  compact JSON, ToolError, preview images
├───────────────────────────────────────────────────────────┤
│ document.py Domain — Document (lxml): element specs,      │  source of truth, pure Python, ~0 ms
│             style normalisation, ids, layers, outline     │
│ engine.py   Inkscape-backed ops on a Document: bboxes,    │  temp file → shell → result
│             run_actions, export, render_png               │
├───────────────────────────────────────────────────────────┤
│ inkscape.py Platform — find_inkscape, InkscapeShell       │  persistent `--shell`, prompt protocol,
│             (persistent process, stderr → errors)         │  stderr classification, auto-restart
└───────────────────────────────────────────────────────────┘
```

## Principles

- **MCP layer stays thin.** No SVG or CLI knowledge in tool handlers.
- **Document owns intent.** Element specs (`{"type": "rect", "fill": ...}`) are the abstraction; SVG details are hidden.
- **Inkscape is a stateless worker.** Each op: write temp SVG → `file-open` → actions/query/export → `file-close`. Never rely on shell state (F5).
- **Platform code is isolated.** Windows `.com` vs `.exe`, process flags live in `inkscape.py`.
- **Stable ids.** Every drawable element gets an id; tools report created/removed ids.

## Request flow

```
agent ──add_elements──► server ──► Document.add (lxml)            ~0 ms
agent ──inspect───────► server ──► Engine.bboxes ──► shell query-all ~60 ms
agent ──path_operation► server ──► Engine.run_actions ──► shell ──► reload lxml
agent ──export────────► server ──► Engine.export ──► temp file ──► move to target
```

## Error model

- `DocumentError` — bad request against the document (unknown id/key/type).
- `InkscapeError` — Inkscape reported a problem on stderr, timed out, or died.
- Both become `ToolError` at the MCP layer, so the agent sees the message.

## Directory layout

```
src/inksmcp/   inkscape.py · document.py · engine.py · server.py
tests/         test_inkscape.py · test_document.py · test_engine.py · test_server.py
experiments/   eNN_*.py — throwaway probes whose findings live in docs/05
docs/          living documentation
```

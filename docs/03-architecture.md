# Architecture

> Draft. Will change after the Phase 0 spikes.

## Layers (proposed)

```
┌──────────────────────────────────────────────┐
│ MCP layer        tools / resources / prompts │  thin: schema, validation, formatting
├──────────────────────────────────────────────┤
│ Domain layer     Document, Layer, Shape,     │  the real abstraction: design concepts
│                  Text, Style, Transform,     │  independent of how they are executed
│                  Exporter                    │
├──────────────────────────────────────────────┤
│ Backends         SvgBackend (direct XML)     │  pluggable executors
│                  InkscapeCliBackend          │
│                  (actions, export, shell)    │
├──────────────────────────────────────────────┤
│ Platform         Inkscape locator, process   │  OS / install specifics isolated here
│                  mgmt, temp files, paths     │
└──────────────────────────────────────────────┘
```

## Principles

- **MCP layer stays thin.** No SVG or CLI knowledge in tool handlers.
- **Domain layer owns intent.** It decides *what* should happen; backends decide *how*.
- **Backends are swappable.** Simple edits go through direct SVG manipulation (fast); geometry-heavy operations (booleans, text-to-path, export) go through Inkscape.
- **Platform code is isolated.** Windows paths, `.com` vs `.exe`, process handling live in one place.
- **Stable ids.** Every object the AI touches has an id it can refer back to.

## Document lifecycle

TBD — open, working copy, snapshots, save.

## Error model

TBD — how failures are reported so an AI can recover.

## Directory layout

TBD — decided once language is chosen.

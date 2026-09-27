# Decision log

One entry per decision. Newest at the bottom. Never delete an entry — mark it **Superseded by D-00X** instead.

## Template

```
## D-00X: <title>
- Date: YYYY-MM-DD
- Status: proposed | accepted | superseded
- Context: why a decision was needed
- Options: A / B / C (with trade-offs)
- Decision: what we chose
- Consequences: what this makes easier / harder
```

---

## D-001: Keep living docs in `docs/` alongside the code
- Date: 2026-09-27
- Status: accepted
- Context: The project will evolve as we learn how Inkscape behaves under automation.
- Decision: Markdown docs in-repo, updated in the same commit as related code.
- Consequences: Docs are versioned with code; history shows how thinking changed.

## D-002: Implementation language & MCP SDK
- Date: 2026-09-27
- Status: proposed
- Options:
  - **Python** (official MCP Python SDK / FastMCP) — Inkscape ships `inkex` in Python; good XML tooling (lxml).
  - **TypeScript/Node** (official MCP TS SDK) — mature MCP ecosystem; would need our own SVG handling.
- Decision: TBD

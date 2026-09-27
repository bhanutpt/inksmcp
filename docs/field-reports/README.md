# Field reports

Reports written by agents (or people) who **used** inksmcp for a real task in a separate session —
not by the session that builds it. They are the "real usage" step of the method in
[../README.md](../README.md): what the agent still had to compute, work around or guess becomes
the next feature, finding or fix.

File name: `YYYY-MM-DD-<task>.md`. Template:

```
# <task>
- Date / client / model:
- Result files:
- Tool calls (approx.) and time:

## What worked well
## What was awkward (agent had to compute, retry, or work around)
## Missing tools or options
## Bugs / surprising behaviour (with the exact call and response)
## Suggestions
```

| Date | Task | Outcome | Follow-ups |
|---|---|---|---|
| 2026-09-27 | [A4 log-log graph paper, 3 x 5 cycles](2026-09-27-log-graph-a4.md) | Done in 14 tool calls; all coordinates computed outside the tools | ✅ All addressed 2026-09-27 (E15, E16): multi-id export fixed, `region` + zoom-by-ids in `render_preview`, `grid` tool, `defaults`, `vertical_anchor`. Same sheet now takes 6 calls, no external script. |

# Inkscape notes

## This machine (verified 2026-09-27)

| Item | Value |
|---|---|
| OS | Windows 11 Home |
| Inkscape | 1.4.4 (dcaf3e7, 2026-05-05) |
| Binary | `C:\Program Files\Inkscape\bin\inkscape.com` (on PATH) |
| Python | 3.12.12 |
| Node | v24.19.0 |
| Git | 2.50.1 |

> On Windows, prefer `inkscape.com` for CLI use — it is the console variant and returns stdout/stderr to the caller; `inkscape.exe` is the GUI variant.

## Integration surfaces to evaluate

| Surface | What it gives | Status |
|---|---|---|
| `--export-*` flags | Headless export (png, pdf, svg, ...) | to test |
| `--actions="a;b;c"` | Run Inkscape actions headless | to test |
| `--action-list` | List all available actions | to test |
| `--shell` | Long-lived interactive process, many commands | to test |
| `--query-*` | Bounding boxes / geometry of objects | to test |
| `inkex` (Python extension API) | Bundled with Inkscape; SVG DOM helpers | to test |
| Direct SVG/XML editing | Fast, no process spawn | to test |

## Findings

_Add dated findings here as spikes and real work reveal behavior._

- TBD

# Getting started

## 1. Install Inkscape

inksmcp drives your installed Inkscape (1.x; developed and tested with 1.4). It looks for it on `PATH`
and in the default install locations, or wherever `INKSCAPE_PATH` points.

| System | Install | Found at |
|---|---|---|
| Windows | [inkscape.org](https://inkscape.org/release/) installer, or `winget install Inkscape.Inkscape` | `C:\Program Files\Inkscape\bin\inkscape.com` |
| macOS | [inkscape.org](https://inkscape.org/release/) disk image, or `brew install --cask inkscape` | `/Applications/Inkscape.app/Contents/MacOS/inkscape` |
| Linux | `sudo add-apt-repository ppa:inkscape.dev/stable && sudo apt install inkscape` (Ubuntu), your distribution's package, or the snap | `/usr/bin/inkscape`, `/snap/bin/inkscape` |

An AppImage works too: set `INKSCAPE_PATH` to the AppImage file. The Flatpak build can't be called
directly (it needs `flatpak run`); use another package or point `INKSCAPE_PATH` at a small wrapper script.

## 2. Install uv

inksmcp is a Python package run by [uv](https://docs.astral.sh/uv/getting-started/installation/)
(`uvx` downloads and runs it in its own environment, no manual Python setup). Check with `uvx --version`.

## 3. Add the server to your client

The server command is `uvx inksmcp` (stdio). To run the development version from GitHub instead, use
`uvx --from git+https://github.com/bhanutpt/inksmcp inksmcp`.

**Claude Code**

```bash
claude mcp add --scope user inkscape -- uvx inksmcp
```

**Claude Desktop**: Settings → Developer → Edit Config, then add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "inkscape": {
      "command": "uvx",
      "args": ["inksmcp"]
    }
  }
}
```

**VS Code** (`.vscode/mcp.json`):

```json
{
  "servers": {
    "inkscape": { "type": "stdio", "command": "uvx", "args": ["inksmcp"] }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`) and most other clients use the Claude Desktop shape above.

If Inkscape is somewhere else, add `"env": {"INKSCAPE_PATH": "/path/to/inkscape"}` to the server entry.

## 4. Try it

Ask your assistant something like:

> Using the inkscape tools, make an A5 flyer for a book swap on Saturday at 10:00 in the library
> garden. Show me a preview, then export a PDF to my Desktop.

A first check is `inkscape_info`, which reports the Inkscape version and path the server found.
To edit an existing drawing, give the assistant its path: *"Open ~/Pictures/logo.svg, make the blue
parts dark green and export a 512 px PNG."*

Next: [recipes](recipes.md) for what the tools can do together, the [tool reference](tools.md) for
every parameter.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Inkscape not found" | Install Inkscape, or set `INKSCAPE_PATH` in the server's `env`. On Windows point it at `inkscape.com` (the console build), not `inkscape.exe`. |
| The first call takes a second or two | The server starts one Inkscape process and keeps it running; later calls take milliseconds. |
| Text renders in a different font | Inkscape falls back silently when a font isn't installed. Use installed fonts, or `text_to_path` on PDF export once the look is right. |
| A linked image disappears after moving files | `image` elements link to files by default; use `embed: true` for a self-contained SVG. |
| An error ends with "(Nothing was changed.)" | Every tool is all-or-nothing: the document is exactly as before the call. Fix the arguments and retry. |
| Windows: `uv run` fails with "os error 32" | A client is holding the server's `inksmcp.exe` open (only when running from a source checkout). Use `uv run --no-sync`, or stop the client first. |

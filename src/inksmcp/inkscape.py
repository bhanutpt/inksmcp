"""Platform layer: locate Inkscape and drive it through a persistent `--shell` process.

Key facts (see docs/05-inkscape-notes.md):
- Inkscape exits 0 even when actions fail; errors only appear on stderr.
- `--shell` answers each command in ~ms vs ~1 s per process spawn.
- The shell echoes every command (with line-editing junk on long lines) before its output,
  and prints "> " as the prompt when ready for the next command.
"""
from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

PROMPT = "> "

# stderr patterns that mean the command did not do what was asked.
_ERROR_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"could not find action",
        r"did not find object",
        r"does not exist",
        r"no document",
        r"^select .*to perform",  # e.g. "Select at least 1 path to perform a boolean union."
        r"failed",
        r"error",
    )
]
# Harmless noise Inkscape/GTK sometimes prints.
_NOISE_PATTERNS = [re.compile(p, re.I) for p in (r"^\s*$", r"gtk-warning", r"fontconfig")]


class InkscapeError(RuntimeError):
    """An Inkscape command failed (detected from stderr, since the exit code is always 0)."""


def find_inkscape() -> Path:
    """Locate the Inkscape CLI binary. `INKSCAPE_PATH` overrides discovery."""
    env = os.environ.get("INKSCAPE_PATH")
    if env:
        return Path(env)
    # On Windows `inkscape.com` is the console build; `inkscape.exe` is the GUI build.
    names = ["inkscape.com", "inkscape"] if sys.platform == "win32" else ["inkscape"]
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    candidates = [
        Path(r"C:\Program Files\Inkscape\bin\inkscape.com"),
        Path("/Applications/Inkscape.app/Contents/MacOS/inkscape"),
        Path("/usr/bin/inkscape"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise InkscapeError("Inkscape not found. Install Inkscape >= 1.0 or set INKSCAPE_PATH.")


def inkscape_version(exe: Path | None = None) -> str:
    exe = exe or find_inkscape()
    out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=60)
    return out.stdout.strip()


def _clean(line: str) -> str:
    return re.sub(r"<[^>]+>", "", line).strip()  # Inkscape embeds GTK markup like <b>


@dataclass
class ShellResult:
    command: str
    output: str
    messages: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    @property
    def errors(self) -> list[str]:
        return [m for m in self.messages if any(p.search(m) for p in _ERROR_PATTERNS)]


class InkscapeShell:
    """A long-lived `inkscape --shell` process. Thread-safe; restarts itself if it dies."""

    def __init__(self, exe: Path | None = None, timeout: float = 120.0):
        self.exe = exe or find_inkscape()
        self.timeout = timeout
        self._proc: subprocess.Popen | None = None
        self._q: queue.Queue[tuple[str, bytes | None]] = queue.Queue()
        self._lock = threading.Lock()

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if self.alive:
            return
        self._q = queue.Queue()
        self._proc = subprocess.Popen(
            [str(self.exe), "--shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for stream, tag in ((self._proc.stdout, "out"), (self._proc.stderr, "err")):
            threading.Thread(target=self._pump, args=(stream, tag, self._q), daemon=True).start()
        self._read_response()  # banner

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def close(self) -> None:
        if not self._proc:
            return
        try:
            if self.alive:
                self._proc.stdin.write(b"quit\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=10)
        except Exception:
            self._proc.kill()
        self._proc = None

    def __enter__(self) -> "InkscapeShell":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- I/O -------------------------------------------------------------
    @staticmethod
    def _pump(stream, tag, q) -> None:
        while True:
            chunk = stream.read1(65536)
            if not chunk:
                q.put((tag, None))
                return
            q.put((tag, chunk))

    def _read_response(self) -> tuple[str, str]:
        out, err = bytearray(), bytearray()
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InkscapeError("Timed out waiting for Inkscape shell.")
            try:
                tag, chunk = self._q.get(timeout=remaining)
            except queue.Empty:
                continue
            if chunk is None:
                if tag == "out":
                    raise InkscapeError("Inkscape shell exited unexpectedly: " + err.decode(errors="replace"))
                continue
            (out if tag == "out" else err).extend(chunk)
            if tag == "out" and out.endswith(PROMPT.encode()):
                break
        # stderr travels on a separate pipe; give it a moment to catch up.
        idle_until = time.monotonic() + 0.015
        while time.monotonic() < idle_until:
            try:
                tag, chunk = self._q.get(timeout=0.005)
            except queue.Empty:
                continue
            if chunk:
                (out if tag == "out" else err).extend(chunk)
                idle_until = time.monotonic() + 0.015
        return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")

    def run(self, command: str, check: bool = True) -> ShellResult:
        """Run one shell line (may contain several `;`-separated actions)."""
        if "\n" in command:
            raise ValueError("Shell commands must be a single line.")
        with self._lock:
            self.start()
            t = time.perf_counter()
            self._proc.stdin.write((command + "\n").encode("utf-8"))
            self._proc.stdin.flush()
            out, err = self._read_response()
            elapsed = (time.perf_counter() - t) * 1000
        out = out.replace("\r\n", "\n")
        # First line is the echoed command (possibly mangled); last is the prompt.
        body = out.split("\n", 1)[1] if "\n" in out else ""
        body = body[: -len(PROMPT)] if body.endswith(PROMPT) else body
        messages = [_clean(l) for l in err.replace("\r\n", "\n").split("\n")]
        messages = [m for m in messages if m and not any(p.search(m) for p in _NOISE_PATTERNS)]
        result = ShellResult(command, body.rstrip("\n"), messages, elapsed)
        if check and result.errors:
            raise InkscapeError("; ".join(result.errors))
        return result

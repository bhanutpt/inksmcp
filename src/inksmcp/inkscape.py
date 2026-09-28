"""Platform layer: locate Inkscape and drive it through a persistent `--shell` process.

Key facts (see docs/development/inkscape-notes.md):
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
        r"was not found",  # e.g. export-id with an unknown id: "... not found in the document. Skipping." (E15)
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


class ShellDied(InkscapeError):
    """The shell process ended while running a command (field report 5, E23). The next command
    starts a fresh shell, so a whole open-run-close pass can simply be retried."""


def _install_paths() -> list[Path]:
    """Where the official installers put Inkscape."""
    if sys.platform == "win32":
        roots = [os.environ.get(k) for k in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
        local = os.environ.get("LOCALAPPDATA")
        paths = [Path(r) / "Inkscape" / "bin" / "inkscape.com" for r in roots if r]
        paths += [Path(local) / "Programs" / "Inkscape" / "bin" / "inkscape.com"] if local else []
        return paths + [Path(r"C:\Program Files\Inkscape\bin\inkscape.com")]
    return [Path("/Applications/Inkscape.app/Contents/MacOS/inkscape"), Path("/opt/homebrew/bin/inkscape"),
            Path("/usr/local/bin/inkscape"), Path("/usr/bin/inkscape"), Path("/snap/bin/inkscape")]


def _console_build(path: Path) -> Path | None:
    """On Windows only inkscape.com answers on stdout; inkscape.exe is the GUI build, and package-manager
    shims (Chocolatey, Scoop) launch that one, so a shell through them stays silent (CI 2026-09-28)."""
    if sys.platform != "win32" or path.suffix.lower() == ".com":
        return path
    sibling = path.with_name("inkscape.com")
    return sibling if sibling.exists() else None


def find_inkscape() -> Path:
    """Locate the Inkscape command-line binary. `INKSCAPE_PATH` overrides discovery. Order: the console build
    on PATH, the official install folders, then anything else on PATH (Windows: only a console build)."""
    env = os.environ.get("INKSCAPE_PATH")
    if env:
        found = _console_build(Path(env))
        if found is None:
            raise InkscapeError(f"INKSCAPE_PATH points at {env}, the GUI build, which doesn't answer on the "
                                "command line; point it at inkscape.com in the same folder.")
        return found
    if sys.platform == "win32":
        on_path = shutil.which("inkscape.com")
        if on_path:
            return Path(on_path)
    for c in _install_paths():
        if c.exists():
            return c
    on_path = shutil.which("inkscape")
    if on_path:
        found = _console_build(Path(on_path))
        if found is not None:
            return found
        raise InkscapeError(f"Found {on_path}, which starts the GUI build of Inkscape (a package-manager shim?): "
                            "it doesn't answer on the command line. Set INKSCAPE_PATH to inkscape.com in "
                            "Inkscape's bin folder.")
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
        self.last_command = ""
        self.restarts = 0

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if self.alive:
            return
        if self._proc is not None:
            self.restarts += 1
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
                    raise self._died(err.decode(errors="replace"))
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

    def _died(self, stderr: str) -> "ShellDied":
        code = None
        try:
            code = self._proc.wait(timeout=2)
        except Exception:
            pass
        cmd = self.last_command if len(self.last_command) <= 160 else self.last_command[:160] + "..."
        return ShellDied(f"Inkscape shell exited unexpectedly (exit code {code}) while running {cmd!r}: "
                         + " ".join(stderr.split()))

    def run(self, command: str, check: bool = True) -> ShellResult:
        """Run one shell line (may contain several `;`-separated actions)."""
        if "\n" in command:
            raise ValueError("Shell commands must be a single line.")
        with self._lock:
            self.start()
            self.last_command = command
            t = time.perf_counter()
            try:
                self._proc.stdin.write((command + "\n").encode("utf-8"))
                self._proc.stdin.flush()
            except OSError as e:  # died since the alive check
                raise self._died(str(e)) from e
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

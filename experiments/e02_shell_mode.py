"""E02: Inkscape --shell as a persistent process — protocol and latency.

Run: python experiments/e02_shell_mode.py
"""
import subprocess
import threading
import queue
import time
from pathlib import Path

INK = r"C:\Program Files\Inkscape\bin\inkscape.com"
OUT = Path(__file__).parent / "out"
SRC = OUT / "e01.svg"  # produced by e01

p = subprocess.Popen([INK, "--shell"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, bufsize=0)
q: queue.Queue = queue.Queue()


def pump(stream, tag):
    while True:
        b = stream.read(1)
        if not b:
            q.put((tag, None))
            return
        q.put((tag, b))


threading.Thread(target=pump, args=(p.stdout, "out"), daemon=True).start()
threading.Thread(target=pump, args=(p.stderr, "err"), daemon=True).start()


def read_until_prompt(timeout=30):
    out, err = bytearray(), bytearray()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            tag, b = q.get(timeout=0.05)
        except queue.Empty:
            continue
        if b is None:
            break
        (out if tag == "out" else err).extend(b)
        if tag == "out" and out.endswith(b"> "):
            break
    # drain stderr that arrived slightly later
    time.sleep(0.05)
    while not q.empty():
        tag, b = q.get()
        if b:
            (out if tag == "out" else err).extend(b)
    return out.decode(errors="replace"), err.decode(errors="replace")


def cmd(line):
    t = time.perf_counter()
    p.stdin.write((line + "\n").encode())
    p.stdin.flush()
    out, err = read_until_prompt()
    dt = (time.perf_counter() - t) * 1000
    print(f"\n>> {line}  [{dt:.0f} ms]")
    if out.strip("> \r\n"):
        print("stdout:", repr(out[:500]))
    if err.strip():
        print("stderr:", repr(err[:500]))


t0 = time.perf_counter()
banner, err = read_until_prompt()
print(f"startup {(time.perf_counter()-t0)*1000:.0f} ms; banner={banner[:200]!r} err={err[:200]!r}")

cmd(f"file-open:{SRC}")
cmd("query-all")
cmd("select-by-id:r1")
cmd("query-x")
cmd("select-clear")
cmd("select-by-id:r1,c1;path-union")
cmd("query-all")
cmd(f"export-filename:{OUT / 'e02_a.png'};export-type:png;export-do")
cmd(f"export-filename:{OUT / 'e02_b.png'};export-do")
cmd("select-by-id:nope")
cmd("not-an-action")
cmd("file-close")
cmd(f"file-open:{SRC}")
cmd("query-all")
p.stdin.write(b"quit\n")
p.stdin.flush()
print("exit rc", p.wait(timeout=10))

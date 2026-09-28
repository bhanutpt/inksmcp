"""E23c: Does another Inkscape process kill our shell? E23b: 5/10/15 idle minutes were harmless on their
own, but the one failing idle run overlapped with pytest (which starts and quits its own shells), and the
comic crash (field report 5) happened while other sessions were working on inksmcp.
Shell A stays open; then another instance does something; then A runs a command.

Run: uv run python experiments/e23c_other_instance.py
"""
import subprocess

from inksmcp.document import Document
from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeShell, find_inkscape

doc = Document.create(100, 100, "mm")
doc.add({"type": "rect", "id": "r", "x": 10, "y": 10, "width": 20, "height": 20})


def trial(name, other):
    a = Engine(InkscapeShell())
    a.bboxes(doc)  # A is running, no document open (the state _close leaves)
    pid = a.shell._proc.pid
    other()
    alive_before = a.shell.alive
    a.bboxes(doc)  # retried on a fresh shell if A died
    print(f"{name:34} A alive before next command={alive_before}  restarts={a.shell.restarts}  "
          f"same pid={a.shell._proc.pid == pid}", flush=True)
    a.close()


def shell_quit():
    with InkscapeShell() as b:
        b.run("action-list")


def shell_killed():
    b = InkscapeShell()
    b.start()
    b._proc.kill()


def one_shot():
    subprocess.run([str(find_inkscape()), "--version"], capture_output=True, timeout=60)


def nothing():
    pass


trial("control (nothing)", nothing)
trial("other shell started + quit", shell_quit)
trial("other shell started + killed", shell_killed)
trial("one-shot inkscape --version", one_shot)

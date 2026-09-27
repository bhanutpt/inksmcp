"""Platform layer: the persistent shell protocol against real Inkscape."""
import pytest

from inksmcp.inkscape import InkscapeError, find_inkscape, inkscape_version


def test_find_and_version():
    exe = find_inkscape()
    assert exe.exists()
    assert inkscape_version(exe).startswith("Inkscape 1.")


def test_shell_is_fast(shell):
    shell.run("select-clear", check=False)  # warm
    r = shell.run("action-list")
    assert "path-union" in r.output
    assert r.elapsed_ms < 500, r.elapsed_ms


def test_unknown_action_raises_even_though_exit_code_is_zero(shell):
    with pytest.raises(InkscapeError, match="could not find action"):
        shell.run("definitely-not-an-action")


def test_missing_file_raises(shell, tmp_path):
    with pytest.raises(InkscapeError, match="does not exist"):
        shell.run(f"file-open:{tmp_path / 'nope.svg'}")


def test_long_command_echo_is_stripped(shell, tmp_path):
    # long lines make the shell emit line-editing junk (\r, \b) in its echo (E02)
    svg = tmp_path / ("x" * 60 + ".svg")
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect id="r" width="5" height="5"/></svg>')
    shell.run(f"file-open:{svg}")
    out = shell.run("query-all").output
    shell.run("file-close")
    assert out.splitlines()[-1] == "r,0,0,5,5"


def test_shell_restarts_after_quit(shell):
    shell._proc.stdin.write(b"quit\n")
    shell._proc.stdin.flush()
    shell._proc.wait(timeout=10)
    assert not shell.alive
    assert "path-union" in shell.run("action-list").output

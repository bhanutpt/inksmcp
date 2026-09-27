import struct

import pytest

from inksmcp.engine import Engine
from inksmcp.inkscape import InkscapeShell


@pytest.fixture(scope="session")
def shell():
    with InkscapeShell() as sh:
        yield sh


@pytest.fixture(scope="session")
def engine(shell):
    eng = Engine(shell)
    yield eng
    eng.close()


def png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", data[16:24])


@pytest.fixture
def anyio_backend():
    return "asyncio"

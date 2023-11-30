import io
from typing import NamedTuple


class NamedFileContents(NamedTuple):
    contents: io.IOBase
    name: str

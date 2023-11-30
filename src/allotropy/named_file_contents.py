import io
from typing import NamedTuple


class NamedFileContents(NamedTuple):
    """
    A file's contents and the name of the file whence they came.

    In order to support use cases where the file contents of a vendor file are not stored locally,
    we accept an IO object for file contents. However, some vendor file parsers extract information
    from the original file name produced by the instrument. Thus, we use a tuple of file contents
    and original file name to support as many cases as possible.
    """

    contents: io.IOBase
    original_file_name: str

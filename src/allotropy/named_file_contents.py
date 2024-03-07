from dataclasses import dataclass

from allotropy.types import IOType


@dataclass(frozen=True)
class NamedFileContents:
    """
    A file's contents and the name of the file whence they came.

    In order to support use cases where the file contents of a vendor file are not stored locally,
    we accept an IO object for file contents. However, some vendor file parsers extract information
    from the original file name produced by the instrument. Thus, we use this class to support
    as many cases as possible.
    """

    contents: IOType
    original_file_name: str

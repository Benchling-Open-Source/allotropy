from dataclasses import dataclass
from typing import Optional

from allotropy.types import IOType


@dataclass(frozen=True)
class NamedFileContents:
    """
    A file's contents, the name of the file whence they came, and an optional encoding.

    In order to support use cases where the file contents of a vendor file are not stored locally,
    we accept an IO object for file contents. However, some vendor file parsers extract information
    from the original file name produced by the instrument. Thus, we use this class to support
    as many cases as possible.

    An encoding of None means that an encoding was not specified. Currently, if encoding is not specified
    (and contents is a bytes object), we assume DEFAULT_ENCODING. If CHARDET_ENCODING is specified, we
    will [try to] use chardet to detect the encoding.
    """

    contents: IOType
    original_file_name: str
    encoding: Optional[str] = None

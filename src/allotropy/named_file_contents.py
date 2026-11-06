from dataclasses import dataclass
from functools import cached_property
from io import BytesIO
from pathlib import PureWindowsPath
from typing import cast, IO

from allotropy.types import IOType


@dataclass(frozen=True)
class NamedFileContents:
    """
    A file's contents, the path of the file whence they came, and an optional encoding.

    In order to support use cases where the file contents of a vendor file are not stored locally,
    we accept an IO object for file contents. However, some vendor file parsers extract information
    from the original file name produced by the instrument. Thus, we use this class to support
    as many cases as possible.

    An encoding of None means that an encoding was not specified. Currently, if encoding is not specified
    (and contents is a bytes object), we assume DEFAULT_ENCODING. If CHARDET_ENCODING is specified, we
    will [try to] use chardet to detect the encoding.
    """

    contents: IOType
    original_file_path: str
    encoding: str | None = None

    @cached_property
    def extension(self) -> str:
        return PureWindowsPath(self.original_file_path).suffix[1:].lower()

    def get_bytes_stream(self, encoding: str = "utf-8") -> BytesIO:
        raw_content = self.contents.read()
        return BytesIO(
            raw_content.encode(encoding)
            if isinstance(raw_content, str)
            else raw_content
        )

    def get_seekable_bytes_stream(self, encoding: str = "utf-8") -> IO[bytes]:
        """Return a seekable binary stream over the contents.

        Unlike get_bytes_stream, this avoids reading the whole file into memory when
        contents is already a seekable binary stream (e.g. a file handle opened by
        allotrope_from_file). Use this for large container formats (zip, OLE) where the
        reader only needs a few members and can seek to them.
        """
        contents = self.contents
        if isinstance(contents.read(0), bytes) and contents.seekable():
            contents.seek(0)
            return cast(IO[bytes], contents)
        return self.get_bytes_stream(encoding)

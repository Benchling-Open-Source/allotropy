from typing import final, Optional

import chardet

from allotropy.exceptions import AllotropeConversionError
from allotropy.types import IOType


@final
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

    def __init__(self, contents: IOType, original_file_name: str) -> None:
        self.contents = contents
        self.original_file_name = original_file_name

    def read_to_lines(self, encoding: Optional[str] = "UTF-8") -> list[str]:
        stream_contents = self.contents.read()
        raw_contents = (
            self._decode(stream_contents, encoding)
            if isinstance(stream_contents, bytes)
            else stream_contents
        )
        contents = raw_contents.replace("\r\n", "\n")
        return contents.split("\n")

    def _decode(self, bytes_content: bytes, encoding: Optional[str]) -> str:
        if not encoding:
            encoding = chardet.detect(bytes_content)["encoding"]
            if not encoding:
                error = (
                    "Unable to detect text encoding for file. The file may be empty."
                )
                raise AllotropeConversionError(error)
        return bytes_content.decode(encoding)

from __future__ import annotations

from io import BytesIO
from re import search
from zipfile import ZipFile

from allotropy.parsers.utils.values import assert_not_none


def fix_zip(data: BytesIO) -> BytesIO:
    # ZipFile can fail if there are excess trailing bytes. This function detects the end of zip's central directory and,
    # if found, truncates the data after the end of the zip file.
    content = data.read()
    pos = content.rfind(
        b"\x50\x4b\x05\x06"
    )  # reverse find: this string of bytes is the end of the zip's central directory.
    if pos > 0:
        data.seek(
            pos + 22
        )  # End bytes size is 22, see https://pkwaredownloads.blob.core.windows.net/pkware-general/Documentation/APPNOTE-6.3.0.TXT
        data.truncate()
        data.seek(0)

    return data


class ZipHandler:
    def __init__(self, data: BytesIO):
        self.zip_file = ZipFile(fix_zip(data))
        self.name_list = self.zip_file.namelist()

    def get_inner_path_or_none(self, pattern: str) -> str | None:
        for file_name in self.name_list:
            if search(pattern, file_name):
                return file_name
        return None

    def get_inner_path(self, pattern: str) -> str:
        return assert_not_none(
            self.get_inner_path_or_none(pattern),
            msg=f"Unable to find file that match pattern {pattern}",
        )

    def get_file(self, inner_path: str) -> BytesIO:
        return BytesIO(self.zip_file.read(inner_path))

    def get_zip(self, inner_path: str) -> ZipHandler:
        return ZipHandler(self.get_file(inner_path))

    def get_file_from_pattern(self, pattern: str) -> BytesIO:
        return self.get_file(self.get_inner_path(pattern))

    def get_zip_from_pattern(self, pattern: str) -> ZipHandler:
        return self.get_zip(self.get_inner_path(pattern))

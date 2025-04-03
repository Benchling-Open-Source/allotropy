from __future__ import annotations

from io import BytesIO
from re import search
from zipfile import ZipFile

from allotropy.parsers.utils.values import assert_not_none


class ZipHandler:
    def __init__(self, data: BytesIO):
        self.zip_file = self.get_zip_file(data)
        self.name_list = self.zip_file.namelist()

    def get_zip_file(self, data: BytesIO) -> ZipFile:
        return ZipFile(data)

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

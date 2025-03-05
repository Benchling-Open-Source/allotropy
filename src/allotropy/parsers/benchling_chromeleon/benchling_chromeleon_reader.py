import json
from typing import Any

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.values import assert_not_none


class BenchlingChromeleonReader:
    SUPPORTED_EXTENSIONS = "json"
    sequence: dict[str, Any]
    injections: list[dict[str, Any]]
    device_information: dict[str, Any]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        contents: dict[str, Any] = json.load(named_file_contents.contents)
        self.sequence: dict[str, Any] = contents.get("sequence", {})
        self.device_information: dict[str, Any] = contents.get("device information", {})
        self.injections: list[dict[str, Any]] = assert_not_none(
            contents.get("injections"), "injections"
        )

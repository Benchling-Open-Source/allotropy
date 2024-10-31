from abc import ABC, abstractmethod
from re import search
from typing import ClassVar

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
)


class Creator(ABC):
    PLUGIN_REGEX: ClassVar[str]
    EXPECTED_SHEETS: ClassVar[list[str]]

    @classmethod
    def check_sheets(cls, reader: DesignQuantstudioReader) -> bool:
        return all(reader.has_sheet(sheet_name) for sheet_name in cls.EXPECTED_SHEETS)

    @classmethod
    def check_plugin_name(cls, raw_plugin_name: str | None) -> bool:
        return (
            True
            if raw_plugin_name is None
            else bool(search(cls.PLUGIN_REGEX, raw_plugin_name))
        )

    @classmethod
    def check_experiment_type(
        cls, reader: DesignQuantstudioReader, raw_plugin_name: str | None
    ) -> bool:
        return cls.check_sheets(reader) and cls.check_plugin_name(raw_plugin_name)

    @classmethod
    @abstractmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        pass

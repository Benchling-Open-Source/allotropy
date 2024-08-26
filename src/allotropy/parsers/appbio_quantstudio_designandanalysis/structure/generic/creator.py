from abc import ABC, abstractmethod
from typing import ClassVar

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
)


class Creator(ABC):
    EXPECTED_SHEETS: ClassVar[list[str]] = []

    @classmethod
    def check_type(cls, reader: DesignQuantstudioReader) -> bool:
        return all(reader.has_sheet(sheet_name) for sheet_name in cls.EXPECTED_SHEETS)

    @classmethod
    @abstractmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        pass

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_NAME
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.timestamp_parser import TimestampParser

Data = TypeVar("Data")
Model = TypeVar("Model")
Mapper = TypeVar("Mapper")


class VendorParser(ABC):
    """Base class for all vendor parsers."""

    # The display name of the parser. Displayed in the README.
    DISPLAY_NAME: str
    # Signifies if the parser is ready to be used. Can be set to ReleaseState.WORKING_DRAFT while being developed.
    RELEASE_STATE: ReleaseState
    # Comma separated list of file extensions that this parser supports.
    SUPPORTED_EXTENSIONS: str

    timestamp_parser: TimestampParser

    def __init__(self, timestamp_parser: TimestampParser | None = None):
        self.timestamp_parser = timestamp_parser or TimestampParser()

    @abstractmethod
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        raise NotImplementedError

    @property
    def asm_converter_name(self) -> str:
        return f'{ASM_CONVERTER_NAME}_{self.DISPLAY_NAME.replace(" ", "_").replace("-", "_")}'.lower()

    def _get_date_time(self, time: str) -> TDateTimeValue:
        return self.timestamp_parser.parse(time)


class MapperVendorParser(VendorParser, Generic[Data, Model]):
    SCHEMA_MAPPER: Callable[..., SchemaMapper[Data, Model]]

    def _get_mapper(self) -> SchemaMapper[Data, Model]:
        return self.SCHEMA_MAPPER(self.asm_converter_name, self._get_date_time)

    @abstractmethod
    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        raise NotImplementedError

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        return self._get_mapper().map_model(self.create_data(named_file_contents))

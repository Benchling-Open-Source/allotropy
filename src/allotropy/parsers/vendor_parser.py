from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from pandas import Timestamp

from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.constants import ASM_CONVERTER_NAME
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.utils.values import assert_not_none

MapperT = TypeVar("MapperT")


class VendorParser(ABC):
    timestamp_parser: TimestampParser

    """Base class for all vendor parsers."""

    def __init__(self, timestamp_parser: TimestampParser):
        self.timestamp_parser = assert_not_none(timestamp_parser, "timestamp_parser")

    @property
    @abstractmethod
    def display_name(self) -> str:
        """The display name of the parser. Displayed in the README."""
        raise NotImplementedError

    @property
    @abstractmethod
    def release_state(self) -> ReleaseState:
        """Signifies if the parser is ready to be used. Can be set to ReleaseState.WORKING_DRAFT while being developed."""
        raise NotImplementedError

    @abstractmethod
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        raise NotImplementedError

    def _get_mapper(self, mapper_cls: Callable[..., MapperT]) -> MapperT:
        return mapper_cls(self.get_asm_converter_name(), self._get_date_time)

    def get_asm_converter_name(self) -> str:
        """Returns the ASM converter name for this parser."""
        return f'{ASM_CONVERTER_NAME}_{self.display_name.replace(" ", "_").replace("-", "_")}'.lower()

    def _get_date_time(self, time: str) -> TDateTimeValue:
        assert_not_none(time, "time")

        return self.timestamp_parser.parse(time)

    # TODO(brian): Calling str() to pass to _get_date_time() potentially loses information.
    def _get_date_time_from_timestamp(self, timestamp: Timestamp) -> TDateTimeValue:
        # TODO(brian): fail if timestamp is not a Timestamp?

        assert_not_none(timestamp, "timestamp")

        time = str(timestamp)
        return self._get_date_time(time)

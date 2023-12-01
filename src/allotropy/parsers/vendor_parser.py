from abc import ABC, abstractmethod
from typing import Any

from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.utils.values import assert_not_none


class VendorParser(ABC):
    timestamp_parser: TimestampParser

    """Base class for all vendor parsers."""

    def __init__(self, timestamp_parser: TimestampParser):
        self.timestamp_parser = assert_not_none(timestamp_parser, "timestamp_parser")

    @abstractmethod
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        raise NotImplementedError

    # TODO: make time param a str
    def _get_date_time(self, time: Any) -> TDateTimeValue:
        assert_not_none(time, "time")

        return self.timestamp_parser.parse(str(time))

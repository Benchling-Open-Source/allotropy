from abc import ABC, abstractmethod
from typing import Any

from pandas import Timestamp

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

    def _get_date_time(self, time: str) -> TDateTimeValue:
        assert_not_none(time, "time")

        return self.timestamp_parser.parse(time)

    # TODO(brian): Calling str() to pass to _get_date_time() potentially loses information.
    def _get_date_time_from_timestamp(self, timestamp: Timestamp) -> TDateTimeValue:
        # TODO(brian): fail if timestamp is not a Timestamp?

        assert_not_none(timestamp, "timestamp")

        time = str(timestamp)
        return self._get_date_time(time)

from abc import ABC, abstractmethod
import io
from typing import Any

from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.utils.values import assert_not_none


class VendorParser(ABC):
    timestamp_parser: TimestampParser

    """Base class for all vendor parsers."""

    def __init__(self, timestamp_parser: TimestampParser):
        self.timestamp_parser = assert_not_none(timestamp_parser, "timestamp_parser")

    def to_allotrope(self, contents: io.IOBase, filename: str) -> Any:
        """
        Parse the contents of a file and return an Allotrope model.

        :param contents: file contests
        :param filename: file name
        :return: an Allotrope model
        """
        return self._parse(contents, filename)

    # TODO: inline this method
    @abstractmethod
    def _parse(self, contents: io.IOBase, filename: str) -> Any:
        raise NotImplementedError

    # TODO: rename to _get_date_time
    def get_date_time(self, time: Any) -> TDateTimeValue:
        assert_not_none(time, "time")

        return self.timestamp_parser.parse(str(time))

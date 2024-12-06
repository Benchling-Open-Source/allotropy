from abc import abstractmethod
from collections.abc import Iterator
import struct


class Converter:
    @abstractmethod
    def get_format(self) -> str:
        pass

    @abstractmethod
    def iter_data(self, data: bytes) -> Iterator[bytes]:
        pass

    def convert(self, data: bytes) -> tuple[float, ...]:
        binary_format = self.get_format()
        return tuple(
            struct.unpack(binary_format, binary_data)[0]
            for binary_data in self.iter_data(data)
        )


class FloatConverter(Converter):
    def get_format(self) -> str:
        return "<f"  # little endian float (4 bytes)

    def iter_data(self, data: bytes) -> Iterator[bytes]:
        for i in range(47, len(data) - 48, 4):
            yield data[i : i + 4]

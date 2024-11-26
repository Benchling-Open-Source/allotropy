from abc import abstractmethod
from collections.abc import Iterator
from io import BytesIO
import struct


class Converter:
    @abstractmethod
    def get_format(self) -> str:
        pass

    @abstractmethod
    def iter_data(self, stream: BytesIO) -> Iterator[bytes]:
        pass

    def convert(self, stream: BytesIO) -> tuple[float, ...]:
        binary_format = self.get_format()
        return tuple(
            struct.unpack(binary_format, data)[0] for data in self.iter_data(stream)
        )


class FloatConverter(Converter):
    def get_format(self) -> str:
        return "<f"  # little endian float (4 bytes)

    def iter_data(self, stream: BytesIO) -> Iterator[bytes]:
        data = stream.read()
        for i in range(47, len(data) - 48, 4):
            yield data[i : i + 4]

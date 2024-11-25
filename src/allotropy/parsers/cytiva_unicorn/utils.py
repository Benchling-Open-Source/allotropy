from io import BytesIO
import struct


def min_to_sec(data: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(element * 60 for element in data)


def parse_data_cube_bynary(stream: BytesIO) -> tuple[float, ...]:
    data = stream.read()
    # assuming little endian float (4 bytes)
    return tuple(
        struct.unpack("<f", data[i : i + 4])[0] for i in range(47, len(data) - 48, 4)
    )

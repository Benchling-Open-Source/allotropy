from io import BytesIO
import struct

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
)
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)


class DataCubeParser:
    def __init__(self, handler: UnicornZipHandler):
        self.dimension_stream = handler.get_file_from_pattern("CoordinateData.Volumes$")
        self.measures_stream = handler.get_file_from_pattern(
            "CoordinateData.Amplitudes$"
        )

    def min_to_sec(self, data: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(element * 60 for element in data)

    def bytes_to_float(self, data: bytes) -> tuple[float, ...]:
        # little endian float (4 bytes)
        return tuple(
            struct.unpack("<f", data[i : i + 4])[0]
            for i in range(47, len(data) - 48, 4)
        )

    def bytes_stream_to_float(self, stream: BytesIO) -> tuple[float, ...]:
        return self.bytes_to_float(stream.read())

    def get_dimensions(self) -> tuple[float, ...]:
        return self.min_to_sec(self.bytes_stream_to_float(self.dimension_stream))

    def get_measures(self) -> tuple[float, ...]:
        return self.bytes_stream_to_float(self.measures_stream)


def get_data_cube_parser(
    handler: UnicornZipHandler,
    curve_element: StrictElement,
) -> DataCubeParser:
    names = ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
    data_name = curve_element.recursive_find(names).get_text()
    return DataCubeParser(handler.get_zip_from_pattern(data_name))


def create_data_cube(
    handler: UnicornZipHandler,
    curve_element: StrictElement,
    data_cuve_component: DataCubeComponent,
) -> DataCube:
    parser = get_data_cube_parser(handler, curve_element)
    return DataCube(
        label=curve_element.find("Name").get_text(),
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="retention time",
                unit="s",
            ),
        ],
        structure_measures=[data_cuve_component],
        dimensions=[parser.get_dimensions()],
        measures=[parser.get_measures()],
    )

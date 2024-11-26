from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.converters import (
    Converter,
    FloatConverter,
)


class DataCubeInfo:
    def __init__(self, handler: UnicornZipHandler, name: str):
        self.data = handler.get_file_from_pattern(f"CoordinateData.{name}$")
        self.type = handler.get_file_from_pattern(f"CoordinateData.{name}DataType$")

    def get_converter(self) -> Converter:
        data_type = self.type.read().decode()

        if data_type.startswith("System.Single"):
            return FloatConverter()

        msg = f"Unable to parse data cube with binary data in format {data_type}"
        raise AllotropeConversionError(msg)


class DataCubeParser:
    def __init__(self, handler: UnicornZipHandler):
        self.dimension_info = DataCubeInfo(handler, "Volumes")
        self.measures_info = DataCubeInfo(handler, "Amplitudes")

    def min_to_sec(self, data: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(element * 60 for element in data)

    def get_data(self, data_cube_info: DataCubeInfo) -> tuple[float, ...]:
        return data_cube_info.get_converter().convert(data_cube_info.data)

    def get_dimensions(self) -> tuple[float, ...]:
        return self.min_to_sec(self.get_data(self.dimension_info))

    def get_measures(self) -> tuple[float, ...]:
        return self.get_data(self.measures_info)

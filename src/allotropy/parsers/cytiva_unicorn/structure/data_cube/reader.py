from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.converters import (
    Converter,
    FloatConverter,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.transformations import (
    Transformation,
)


class DataCubeReader:
    def __init__(
        self,
        handler: UnicornZipHandler,
        name: str,
        transformation: Transformation | None = None,
    ):
        self.transformation = transformation

        self.data_stream = handler.get_file_from_pattern(f"CoordinateData.{name}$")
        self.type_stream = handler.get_file_from_pattern(
            f"CoordinateData.{name}DataType$"
        )

        self.data = self.data_stream.read()
        self.type = self.type_stream.read().decode()

    def get_converter(self) -> Converter:
        if self.type.startswith("System.Single"):
            return FloatConverter()

        msg = f"Unable to parse data cube with binary data in format {self.type}"
        raise AllotropeConversionError(msg)

    def get_data(self) -> tuple[float, ...]:
        data = self.get_converter().convert(self.data)
        return self.transformation.transform(data) if self.transformation else data

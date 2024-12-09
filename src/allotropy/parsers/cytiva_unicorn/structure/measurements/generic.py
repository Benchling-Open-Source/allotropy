from re import search

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
    Measurement,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.creator import (
    create_data_cube,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.transformations import (
    Transformation,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)
from allotropy.parsers.utils.uuids import random_uuid_str


class UnicornMeasurement(Measurement):
    @classmethod
    def filter_curve(
        cls, curve_elements: list[StrictXmlElement], pattern: str
    ) -> StrictXmlElement:
        for element in curve_elements:
            if search(pattern, element.find("Name").get_text()):
                return element
        msg = f"Unable to find curve element with pattern {pattern}"
        raise AllotropeConversionError(msg)

    @classmethod
    def get_data_cube_handler(
        cls, handler: UnicornZipHandler, curve_element: StrictXmlElement
    ) -> UnicornZipHandler:
        names = ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
        data_name = curve_element.recursive_find(names).get_text()
        return handler.get_zip_from_pattern(data_name)

    @classmethod
    def get_data_cube(
        cls,
        handler: UnicornZipHandler,
        curve: StrictXmlElement,
        data_cube_component: DataCubeComponent,
        transformation: Transformation | None = None,
    ) -> DataCube:
        return create_data_cube(
            cls.get_data_cube_handler(handler, curve),
            curve.find("Name").get_text(),
            data_cube_component,
            transformation,
        )

    @classmethod
    def get_measurement(
        cls,
        static_docs: StaticDocs,
        device_control_docs: list[DeviceControlDoc],
        chromatogram_data_cube: DataCube | None = None,
        processed_data_chromatogram_data_cube: DataCube | None = None,
        derived_column_pressure_data_cube: DataCube | None = None,
    ) -> Measurement:
        return Measurement(
            measurement_identifier=random_uuid_str(),
            chromatography_serial_num=static_docs.chromatography_serial_num,
            column_inner_diameter=static_docs.column_inner_diameter,
            chromatography_chemistry_type=static_docs.chromatography_chemistry_type,
            chromatography_particle_size=static_docs.chromatography_particle_size,
            injection_identifier=static_docs.injection_identifier,
            injection_time=static_docs.injection_time,
            autosampler_injection_volume_setting=static_docs.autosampler_injection_volume_setting,
            sample_identifier=static_docs.sample_identifier,
            batch_identifier=static_docs.batch_identifier,
            chromatogram_data_cube=chromatogram_data_cube,
            device_control_docs=device_control_docs,
            processed_data_chromatogram_data_cube=processed_data_chromatogram_data_cube,
            derived_column_pressure_data_cube=derived_column_pressure_data_cube,
        )

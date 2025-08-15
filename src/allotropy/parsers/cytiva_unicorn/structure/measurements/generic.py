from __future__ import annotations

from re import search
from typing import Any

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
    Measurement,
    Peak,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
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
    def get_device_control_custom_info(
        cls, base_element: StrictXmlElement | None
    ) -> dict[str, Any]:
        if not base_element:
            return {}
        return {
            "ColumnVolume": base_element.get_sub_text_or_none("ColumnVolume"),
            "ScanInterval": base_element.get_sub_text_or_none("ScanInterval"),
        }

    @classmethod
    def get_processed_data_custom_info(
        cls, base_element: StrictXmlElement | None
    ) -> dict[str, Any]:
        if not base_element:
            return {}
        return {
            "AmplitudePrecision": base_element.get_sub_text_or_none(
                "AmplitudePrecision"
            ),
            "AmplitudeUnit": base_element.get_sub_text_or_none("AmplitudeUnit"),
            "ChromatogramID": base_element.get_sub_text_or_none("ChromatogramID"),
            "ChromatogramName": base_element.get_sub_text_or_none("ChromatogramName"),
            "ChromatogramStartTime": base_element.get_sub_text_or_none(
                "ChromatogramStartTime"
            ),
            "ChromatogramStartTimeUtcOffsetMinutes": base_element.get_sub_text_or_none(
                "ChromatogramStartTimeUtcOffsetMinutes"
            ),
            "ColumnVolumeUnitName": base_element.get_sub_text_or_none(
                "ColumnVolumeUnitName"
            ),
            "CurveDataType": base_element.get_attr_or_none("CurveDataType"),
            "CurveNumber": base_element.get_sub_text_or_none("CurveNumber"),
            "DistanceBetweenPoints": base_element.get_sub_text_or_none(
                "DistanceBetweenPoints"
            ),
            "DistancetoStartPoints": base_element.get_sub_text_or_none(
                "DistancetoStartPoints"
            ),
            "IsExternal": base_element.get_sub_text_or_none("IsExternal"),
            "IsOriginalData": base_element.get_sub_text_or_none("IsOriginalData"),
            "IsReadOnly": base_element.get_sub_text_or_none("IsReadOnly"),
            "IsoChroneType": base_element.get_sub_text_or_none("IsoChroneType"),
            "MethodStartTime": base_element.get_sub_text_or_none("MethodStartTime"),
            "MethodStartTimeUtcOffsetMinutes": base_element.get_sub_text_or_none(
                "MethodStartTimeUtcOffsetMinutes"
            ),
            "TimeUnit": base_element.get_sub_text_or_none("TimeUnit"),
            "VolumeUnit": base_element.get_sub_text_or_none("VolumeUnit"),
            **base_element.get_unread(),
        }

    @classmethod
    def filter_curve_or_none(
        cls, curve_elements: list[StrictXmlElement], pattern: str
    ) -> StrictXmlElement | None:
        for element in curve_elements:
            name_element = element.find("Name")
            if name := name_element.get_text_or_none():
                if search(pattern, name):
                    return element
        return None

    @classmethod
    def get_data_cube_handler_or_none(
        cls, handler: UnicornZipHandler, curve_element: StrictXmlElement
    ) -> UnicornZipHandler | None:
        names = ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
        if data_name := curve_element.recursive_find_or_none(names):
            if name := data_name.get_text_or_none():
                return handler.get_zip_from_pattern(name)
        return None

    @classmethod
    def get_data_cube_or_none(
        cls,
        handler: UnicornZipHandler,
        curve: StrictXmlElement | None,
        data_cube_component: DataCubeComponent,
        transformation: Transformation | None = None,
    ) -> DataCube | None:
        if curve is None:
            return None

        if data_cube_handler := cls.get_data_cube_handler_or_none(handler, curve):
            name_element = curve.find("Name")

            if name := name_element.get_text_or_none():
                data_cube = create_data_cube(
                    data_cube_handler,
                    name,
                    data_cube_component,
                    transformation,
                )
                return data_cube
        return None

    @classmethod
    def get_measurement(
        cls,
        static_docs: StaticDocs,
        device_control_docs: list[DeviceControlDoc],
        chromatogram_data_cube: DataCube | None = None,
        processed_data_chromatogram_data_cube: DataCube | None = None,
        derived_column_pressure_data_cube: DataCube | None = None,
        peaks: list[Peak] | None = None,
        processed_data_custom_info: dict[str, Any] | None = None,
    ) -> UnicornMeasurement:
        return UnicornMeasurement(
            measurement_identifier=random_uuid_str(),
            chromatography_serial_num=static_docs.chromatography_serial_num,
            column_inner_diameter=static_docs.column_inner_diameter,
            chromatography_chemistry_type=static_docs.chromatography_chemistry_type,
            chromatography_particle_size=static_docs.chromatography_particle_size,
            void_volume=static_docs.void_volume,
            injection_identifier=static_docs.injection_identifier,
            injection_time=static_docs.injection_time,
            autosampler_injection_volume_setting=static_docs.autosampler_injection_volume_setting,
            sample_identifier=static_docs.sample_identifier,
            batch_identifier=static_docs.batch_identifier,
            flow_rate=static_docs.flow_rate,
            chromatogram_data_cube=chromatogram_data_cube,
            device_control_docs=device_control_docs,
            processed_data_chromatogram_data_cube=processed_data_chromatogram_data_cube,
            derived_column_pressure_data_cube=derived_column_pressure_data_cube,
            sample_custom_info={
                "sample_identifier_2": static_docs.sample_identifier_2,
                "sample_identifier_3": static_docs.sample_identifier_3,
                "sample_volume_2": static_docs.sample_volume_2,
                "sample_volume_3": static_docs.sample_volume_3,
            },
            peaks=peaks,
            processed_data_custom_info=processed_data_custom_info,
        )

    @classmethod
    def is_valid(cls, data_cubes: list[DataCube | None]) -> bool:
        return any(data_cube is not None for data_cube in data_cubes)

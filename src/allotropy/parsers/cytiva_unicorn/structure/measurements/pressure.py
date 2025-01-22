from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.generic import (
    UnicornMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)


class PressureMeasurement(UnicornMeasurement):
    @classmethod
    def create_or_none(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
    ) -> UnicornMeasurement | None:
        measurement = cls.get_measurement(
            static_docs=static_docs,
            derived_column_pressure_data_cube=cls.get_data_cube_or_none(
                handler,
                cls.filter_curve_or_none(elements, r"^DeltaC pressure$"),
                DataCubeComponent(
                    type_=FieldComponentDatatype.float,
                    concept="delta column pressure",
                    unit="MPa",
                ),
            ),
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    start_time=static_docs.start_time,
                    pre_column_pressure_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^PreC pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="pre-column pressure",
                            unit="MPa",
                        ),
                    ),
                    sample_pressure_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^Sample pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample pressure",
                            unit="MPa",
                        ),
                    ),
                    system_pressure_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^System pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="system pressure",
                            unit="MPa",
                        ),
                    ),
                    post_column_pressure_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^PostC pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="post-column pressure",
                            unit="MPa",
                        ),
                    ),
                ),
            ],
        )
        return measurement if cls.is_valid(cls.get_data_cubes(measurement)) else None

    @classmethod
    def get_data_cubes(cls, measurement: UnicornMeasurement) -> list[DataCube | None]:
        return [
            measurement.derived_column_pressure_data_cube,
            measurement.device_control_docs[0].pre_column_pressure_data_cube,
            measurement.device_control_docs[0].sample_pressure_data_cube,
            measurement.device_control_docs[0].system_pressure_data_cube,
            measurement.device_control_docs[0].post_column_pressure_data_cube,
        ]

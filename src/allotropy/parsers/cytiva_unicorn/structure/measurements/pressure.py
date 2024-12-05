from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCubeComponent,
    DeviceControlDoc,
    Measurement,
    ProcessedDataDoc,
)
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
    def create(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
    ) -> Measurement:
        return cls.get_measurement(
            static_docs=static_docs,
            processed_data_doc=ProcessedDataDoc(
                derived_column_pressure_data_cube=cls.get_data_cube(
                    handler,
                    cls.filter_curve(elements, r"^DeltaC pressure$"),
                    DataCubeComponent(
                        type_=FieldComponentDatatype.float,
                        concept="delta column pressure",
                        unit="MPa",
                    ),
                )
            ),
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    pre_column_pressure_data_cube=cls.get_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^PreC pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="pre-column pressure",
                            unit="MPa",
                        ),
                    ),
                    sample_pressure_data_cube=cls.get_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^Sample pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample pressure",
                            unit="MPa",
                        ),
                    ),
                    system_pressure_data_cube=cls.get_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^System pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="system pressure",
                            unit="MPa",
                        ),
                    ),
                    post_column_pressure_data_cube=cls.get_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^PostC pressure$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="post-column pressure",
                            unit="MPa",
                        ),
                    ),
                ),
            ],
        )

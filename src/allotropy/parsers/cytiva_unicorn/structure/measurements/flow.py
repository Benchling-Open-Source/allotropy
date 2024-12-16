from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
    Measurement,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCubeComponent
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


class FlowMeasurement(UnicornMeasurement):
    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
    ) -> Measurement:
        return cls.get_measurement(
            static_docs=static_docs,
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    sample_flow_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^Sample flow \(CV/h\)$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample flow",
                            unit="CV/h",
                        ),
                    ),
                    system_flow_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^System flow \(CV/h\)$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="system flow",
                            unit="CV/h",
                        ),
                    ),
                ),
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    sample_flow_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^Sample flow$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample flow",
                            unit="mL/min",
                        ),
                    ),
                    system_flow_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^System flow$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="system flow",
                            unit="mL/min",
                        ),
                    ),
                ),
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    sample_flow_data_cube=cls.get_data_cube_or_none(
                        handler,
                        cls.filter_curve_or_none(elements, r"^Sample linear flow$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample flow",
                            unit="cm/s",
                        ),
                    ),
                ),
            ],
        )

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCubeComponent,
    DeviceControlDoc,
    Measurement,
)
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.generic import (
    UnicornMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.uuids import random_uuid_str


class FlowMeasurement(UnicornMeasurement):
    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictElement],
        static_docs: StaticDocs,
    ) -> Measurement:
        return Measurement(
            measurement_identifier=random_uuid_str(),
            chromatography_column_doc=static_docs.chromatography_doc,
            injection_doc=static_docs.injection_doc,
            sample_doc=static_docs.sample_doc,
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    sample_flow_data_cube=UnicornMeasurement.create_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^Sample flow \(CV/h\)$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample flow",
                            unit="CV/h",
                        ),
                    ),
                    system_flow_data_cube=UnicornMeasurement.create_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^System flow \(CV/h\)$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="system flow",
                            unit="CV/h",
                        ),
                    ),
                ),
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    sample_flow_data_cube=UnicornMeasurement.create_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^Sample flow$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample flow",
                            unit="mL/min",
                        ),
                    ),
                    system_flow_data_cube=UnicornMeasurement.create_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^System flow$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="system flow",
                            unit="mL/min",
                        ),
                    ),
                ),
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    sample_flow_data_cube=UnicornMeasurement.create_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^Sample linear flow$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="sample flow",
                            unit="cm/s",
                        ),
                    ),
                ),
            ],
        )

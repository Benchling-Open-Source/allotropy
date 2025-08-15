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


class FlowMeasurement(UnicornMeasurement):
    @classmethod
    def create_device_control(
        cls,
        device_type: str,
        start_time: str | None,
        sample_flow_data_cube: DataCube | None = None,
        system_flow_data_cube: DataCube | None = None,
    ) -> DeviceControlDoc | None:
        if sample_flow_data_cube is None and system_flow_data_cube is None:
            return None
        return DeviceControlDoc(
            device_type=device_type,
            start_time=start_time,
            sample_flow_data_cube=sample_flow_data_cube,
            system_flow_data_cube=system_flow_data_cube,
        )

    @classmethod
    def create_or_none(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
    ) -> UnicornMeasurement | None:
        device_controls = [
            cls.create_device_control(
                device_type=DEVICE_TYPE,
                start_time=static_docs.start_time,
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
            cls.create_device_control(
                device_type=DEVICE_TYPE,
                start_time=static_docs.start_time,
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
            cls.create_device_control(
                device_type=DEVICE_TYPE,
                start_time=static_docs.start_time,
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
        ]

        measurement = cls.get_measurement(
            static_docs=static_docs,
            device_control_docs=[
                device_control for device_control in device_controls if device_control
            ],
        )
        return measurement if cls.is_valid(cls.get_data_cubes(measurement)) else None

    @classmethod
    def get_data_cubes(cls, measurement: UnicornMeasurement) -> list[DataCube | None]:
        data_cubes = []
        for device_control in measurement.device_control_docs:
            data_cubes.append(device_control.sample_flow_data_cube)
            data_cubes.append(device_control.system_flow_data_cube)
        return data_cubes

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


class TemperatureMeasurement(UnicornMeasurement):
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
                    temperature_profile_data_cube=cls.get_data_cube(
                        handler,
                        cls.filter_curve(elements, r"^Cond temp$"),
                        DataCubeComponent(
                            type_=FieldComponentDatatype.float,
                            concept="temperature",
                            unit="degC",
                        ),
                    ),
                ),
            ],
        )

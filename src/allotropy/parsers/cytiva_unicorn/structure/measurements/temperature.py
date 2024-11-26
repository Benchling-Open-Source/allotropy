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
from allotropy.parsers.cytiva_unicorn.structure.data_cube.creator import (
    create_data_cube,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.generic import (
    UnicornMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.uuids import random_uuid_str


class TemperatureMeasurement(UnicornMeasurement):
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
                    temperature_profile_data_cube=create_data_cube(
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

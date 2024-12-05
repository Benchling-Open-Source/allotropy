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
from allotropy.parsers.cytiva_unicorn.structure.data_cube.transformations import (
    MScm2Sm,
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
from allotropy.parsers.utils.uuids import random_uuid_str


class ConductivityMeasurement(UnicornMeasurement):
    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
    ) -> Measurement:
        return Measurement(
            measurement_identifier=random_uuid_str(),
            chromatography_column_doc=static_docs.chromatography_doc,
            injection_doc=static_docs.injection_doc,
            sample_doc=static_docs.sample_doc,
            chromatogram_data_cube=cls.get_data_cube(
                handler,
                cls.filter_curve(elements, r"^Cond$"),
                DataCubeComponent(
                    type_=FieldComponentDatatype.float,
                    concept="electric conductivity",
                    unit="S/m",
                ),
                transformation=MScm2Sm(),
            ),
            processed_data_doc=ProcessedDataDoc(
                chromatogram_data_cube=cls.get_data_cube(
                    handler,
                    cls.filter_curve(elements, r"^% Cond$"),
                    DataCubeComponent(
                        type_=FieldComponentDatatype.float,
                        concept="electric conductivity",
                        unit="%",
                    ),
                )
            ),
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                )
            ],
        )

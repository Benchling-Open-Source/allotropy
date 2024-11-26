from abc import abstractmethod

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCubeComponent,
    DeviceControlDoc,
    Measurement,
)
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    UnicornFileHandler,
)
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.generic import (
    UnicornMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.uuids import random_uuid_str


class AbsorbanceMeasurement(UnicornMeasurement):
    @classmethod
    @abstractmethod
    def get_curve_regex(cls) -> str:
        pass

    @classmethod
    def get_data_cube_component(cls) -> DataCubeComponent:
        return DataCubeComponent(
            type_=FieldComponentDatatype.float,
            concept="absorbance",
            unit="mAU",
        )

    @classmethod
    def create(
        cls,
        handler: UnicornFileHandler,
        elements: list[StrictElement],
        stat_docs: StaticDocs,
    ) -> Measurement:
        return Measurement(
            measurement_identifier=random_uuid_str(),
            chromatography_column_doc=stat_docs.chromatography_doc,
            injection_doc=stat_docs.injection_doc,
            sample_doc=stat_docs.sample_doc,
            chromatogram_data_cube=cls.create_data_cube(
                handler,
                handler.filter_curve(elements, cls.get_curve_regex()),
                cls.get_data_cube_component(),
            ),
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                )
            ],
        )


class AbsorbanceMeasurement1(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 1_\d+$"


class AbsorbanceMeasurement2(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 2_\d+$"


class AbsorbanceMeasurement3(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 3_\d+$"

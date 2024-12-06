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


class AbsorbanceMeasurement(UnicornMeasurement):
    @classmethod
    @abstractmethod
    def get_curve_regex(cls) -> str:
        pass

    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
    ) -> Measurement:
        return cls.get_measurement(
            static_docs=static_docs,
            chromatogram_data_cube=cls.get_data_cube(
                handler,
                cls.filter_curve(elements, cls.get_curve_regex()),
                DataCubeComponent(
                    type_=FieldComponentDatatype.float,
                    concept="absorbance",
                    unit="mAU",
                ),
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

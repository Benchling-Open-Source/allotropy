from abc import abstractmethod

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCubeComponent
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.generic import (
    UnicornMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.peaks import (
    create_peaks,
    PeakTables,
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
    def create_or_none(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
        peak_tables: PeakTables,
    ) -> UnicornMeasurement | None:
        element = cls.filter_curve_or_none(elements, cls.get_curve_regex())
        if element is None:
            return None
        data_cube = cls.get_data_cube_or_none(
            handler,
            element,
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="absorbance",
                unit="mAU",
            ),
        )
        if data_cube is None:
            return None
        measurement = cls.get_measurement(
            static_docs=static_docs,
            chromatogram_data_cube=data_cube,
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                    start_time=static_docs.start_time,
                    device_control_custom_info=cls.get_device_control_custom_info(
                        element
                    ),
                )
            ],
            peaks=create_peaks(peak_tables, element),
            processed_data_custom_info=cls.get_processed_data_custom_info(element),
        )
        return measurement


class AbsorbanceMeasurement1(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV( ?1_\d+)?$"


class AbsorbanceMeasurement2(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV ?2_\d+$"


class AbsorbanceMeasurement3(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV ?3_\d+$"

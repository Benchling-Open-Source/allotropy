from abc import abstractmethod

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
    Peak,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCubeComponent
from allotropy.parsers.cytiva_unicorn.constants import (
    DEVICE_TYPE,
    PEAK_AREA_UNIT,
    PEAK_END_UNIT,
    PEAK_START_UNIT,
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
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


class AbsorbanceMeasurement(UnicornMeasurement):
    @classmethod
    @abstractmethod
    def get_curve_regex(cls) -> str:
        pass

    @classmethod
    def get_peaks(cls, _: UnicornZipHandler) -> list[Peak]:
        return []

    @classmethod
    def create_or_none(
        cls,
        handler: UnicornZipHandler,
        elements: list[StrictXmlElement],
        static_docs: StaticDocs,
    ) -> UnicornMeasurement:
        return cls.get_measurement(
            static_docs=static_docs,
            chromatogram_data_cube=assert_not_none(
                cls.get_data_cube_or_none(
                    handler,
                    cls.filter_curve_or_none(elements, cls.get_curve_regex()),
                    DataCubeComponent(
                        type_=FieldComponentDatatype.float,
                        concept="absorbance",
                        unit="mAU",
                    ),
                ),
                msg="Unable to find information to create absorbance data cubes.",
            ),
            device_control_docs=[
                DeviceControlDoc(
                    device_type=DEVICE_TYPE,
                )
            ],
            peaks=cls.get_peaks(handler),
        )


class AbsorbanceMeasurement1(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 1_\d+$"

    @classmethod
    def get_peaks(cls, handler: UnicornZipHandler) -> list[Peak]:
        chrom_1 = handler.get_chrom_1()
        peaks = chrom_1.recursive_find_or_none(["PeakTables", "PeakTable", "Peaks"])
        return [
            Peak(
                identifier=random_uuid_str(),
                index=f"Peak {idx}",
                end=peak.get_sub_float_or_none("EndPeakRetention"),
                end_unit=PEAK_END_UNIT,
                height=peak.get_sub_float_or_none("Height"),
                written_name=peak.get_sub_text_or_none("Name"),
                area=peak.get_sub_float_or_none("Area"),
                area_unit=PEAK_AREA_UNIT,
                relative_area=peak.get_sub_float_or_none("PercentOfTotalPeakArea"),
                start=peak.get_sub_float_or_none("StartPeakRetention"),
                start_unit=PEAK_START_UNIT,
                chromatographic_resolution=peak.get_sub_float_or_none("Resolution"),
                width_at_half_height=peak.get_sub_float_or_none("WidthAtHalfHeight"),
                width=peak.get_sub_float_or_none("Width"),
                chromatographic_asymmetry=peak.get_sub_float_or_none("Asymmetry"),
                custom_info={
                    "max peak retention": peak.get_sub_float_or_none("MaxPeakRetention"),
                    "percent of total area": peak.get_sub_float_or_none("PercentOfTotalArea"),
                    "start peak end point height": peak.get_sub_float_or_none("StartPeakEndpointHeight"),
                    "end peak end point height": peak.get_sub_float_or_none("EndPeakEndpointHeight"),
                    "sigma": peak.get_sub_float_or_none("Sigma"),
                    "assymetry peak start": peak.get_sub_float_or_none("AssymetryPeakStart"),
                    "assymetry peak end": peak.get_sub_float_or_none("AssymetryPeakEnd"),
                    "start conductivity height": peak.get_sub_float_or_none("StartConductivityHeight"),
                    "max conductivity height": peak.get_sub_float_or_none("MaxConductivityHeight"),
                    "end conductivity height": peak.get_sub_float_or_none("EndConductivityHeight"),
                    "average conductivity": peak.get_sub_float_or_none("AverageConductivity"),
                }
            )
            for idx, peak in enumerate(peaks.findall("Peak") if peaks else [])
        ]


class AbsorbanceMeasurement2(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 2_\d+$"


class AbsorbanceMeasurement3(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 3_\d+$"

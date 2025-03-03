from abc import abstractmethod

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilliliter,
    TQuantityValuePercent,
    TQuantityValueSeimensPerMeter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TQuantityValue,
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
    PEAK_WIDTH_AT_HALF_HEIGHT_UNIT,
    PEAK_WIDTH_UNIT,
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
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


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
                    start_time=static_docs.start_time,
                )
            ],
            peaks=cls.get_peaks(handler),
        )


class AbsorbanceMeasurement1(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 1_\d+$"

    @classmethod
    def get_peaks_custom_info(
        cls, peak: StrictXmlElement
    ) -> dict[str, TQuantityValue | None]:
        start_conduct_height = peak.get_sub_float_or_none("StartConductivityHeight")
        max_conductivity_height = peak.get_sub_float_or_none("MaxConductivityHeight")
        end_conductivity_height = peak.get_sub_float_or_none("EndConductivityHeight")
        average_conductivity = peak.get_sub_float_or_none("AverageConductivity")

        return {
            "max peak retention": quantity_or_none(
                TQuantityValueMilliliter,
                peak.get_sub_float_or_none("MaxPeakRetention"),
            ),
            "percent of total area": quantity_or_none(
                TQuantityValuePercent,
                peak.get_sub_float_or_none("PercentOfTotalArea"),
            ),
            "start peak end point height": quantity_or_none(
                TQuantityValueMilliAbsorbanceUnit,
                peak.get_sub_float_or_none("StartPeakEndpointHeight"),
            ),
            "end peak end point height": quantity_or_none(
                TQuantityValueMilliAbsorbanceUnit,
                peak.get_sub_float_or_none("EndPeakEndpointHeight"),
            ),
            "sigma": quantity_or_none(
                TQuantityValueUnitless,
                peak.get_sub_float_or_none("Sigma"),
            ),
            "asymmetry peak start": quantity_or_none(
                TQuantityValueUnitless,
                peak.get_sub_float_or_none("AssymetryPeakStart"),
            ),
            "asymmetry peak end": quantity_or_none(
                TQuantityValueUnitless,
                peak.get_sub_float_or_none("AssymetryPeakEnd"),
            ),
            "start conductivity height": (
                TQuantityValueSeimensPerMeter(value=start_conduct_height / 10)
                if start_conduct_height
                else None
            ),
            "max conductivity height": (
                TQuantityValueSeimensPerMeter(value=max_conductivity_height / 10)
                if max_conductivity_height
                else None
            ),
            "end conductivity height": (
                TQuantityValueSeimensPerMeter(value=end_conductivity_height / 10)
                if end_conductivity_height
                else None
            ),
            "average conductivity": (
                TQuantityValueSeimensPerMeter(value=average_conductivity / 10)
                if average_conductivity
                else None
            ),
        }

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
                height_unit="mAu",
                written_name=peak.get_sub_text_or_none("Name"),
                area=peak.get_sub_float_or_none("Area"),
                area_unit=PEAK_AREA_UNIT,
                relative_area=peak.get_sub_float_or_none("PercentOfTotalPeakArea"),
                start=peak.get_sub_float_or_none("StartPeakRetention"),
                start_unit=PEAK_START_UNIT,
                chromatographic_resolution=peak.get_sub_float_or_none("Resolution"),
                width_at_half_height=peak.get_sub_float_or_none("WidthAtHalfHeight"),
                width_at_half_height_unit=PEAK_WIDTH_AT_HALF_HEIGHT_UNIT,
                width=peak.get_sub_float_or_none("Width"),
                width_unit=PEAK_WIDTH_UNIT,
                chromatographic_asymmetry=peak.get_sub_float_or_none("Assymetry"),
                custom_info=cls.get_peaks_custom_info(peak),
            )
            for idx, peak in enumerate(peaks.findall("Peak") if peaks else [], start=1)
        ]


class AbsorbanceMeasurement2(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 2_\d+$"


class AbsorbanceMeasurement3(AbsorbanceMeasurement):
    @classmethod
    def get_curve_regex(cls) -> str:
        return r"^UV 3_\d+$"

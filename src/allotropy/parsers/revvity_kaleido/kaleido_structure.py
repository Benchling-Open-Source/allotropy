from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import logging
import re

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ScanPositionSettingPlateReader,
    TransmittedLightSetting,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_float_or_none,
)


class ExperimentType(Enum):
    FLUORESCENCE = "fluorescence"
    ABSORBANCE = "absorbance"
    LUMINESCENCE = "luminescence"
    OPTICAL_IMAGING = "optical imaging"


class Version(Enum):
    V2 = "2.0"
    V3 = "3.0"


PLATEMAP_TO_SAMPLE_ROLE_TYPE = {
    "B": SampleRoleType.blank_role.value,
    "C": SampleRoleType.control_sample_role.value,
    "S": SampleRoleType.standard_sample_role.value,
    "U": SampleRoleType.unknown_sample_role.value,
    "E": SampleRoleType.control_sample_role.value,
    "ZL": SampleRoleType.control_sample_role.value,
    "ZH": SampleRoleType.control_sample_role.value,
    "LB": SampleRoleType.control_sample_role.value,
    "LC": SampleRoleType.control_sample_role.value,
    "LH": SampleRoleType.control_sample_role.value,
}


SCAN_POSITION_CONVERSION = {
    "TOP": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
    "BOTTOM": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
}


TRANSMITTED_LIGHT_CONVERSION = {
    "BRIGHTFIELD": TransmittedLightSetting.brightfield,
    "DARKFIELD": TransmittedLightSetting.darkfield,
    "PHASE CONTRAST": TransmittedLightSetting.phase_contrast,
}


@dataclass
class BackgroundInfo:
    experiment_type: str


@dataclass(frozen=True)
class Results:
    barcode: str
    data: dict[str, str]

    def get_plate_well_count(self) -> int:
        return len(self.data)

    def get_well_float_value(self, well_position: str) -> float:
        return try_float(
            self.get_well_str_value(well_position),
            f"result well at '{well_position}'",
        )

    def get_well_str_value(self, well_position: str) -> str:
        return str(
            assert_not_none(
                self.data.get(well_position),
                msg=f"Unable to get well at position '{well_position}' from results section.",
            )
        )


@dataclass(frozen=True)
class AnalysisResult:
    analysis_parameter: str
    results: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> AnalysisResult | None:
        barcode_line = assert_not_none(
            reader.drop_until_inclusive("^Barcode:(.+),"),
            msg="Unable to find background information.",
        )

        analysis_parameter = None
        for element in barcode_line.split(","):
            if re.search("^.+:.+$", element):
                key, value = element.split(":", maxsplit=1)
                if "AnalysisParameter" in key:
                    analysis_parameter = value
                    break

        analysis_parameter = assert_not_none(
            analysis_parameter,
            msg="Unable to find analysis parameter in Analysis Results section.",
        )

        try:
            results_df = assert_not_none(
                reader.pop_csv_block_as_df(header=0, index_col=0),
                msg="Unable to find results table.",
            )
        except AllotropeConversionError:
            logging.warning(
                f"Unable to read analysis result '{analysis_parameter}'. Ignoring"
            )
            return None

        for column in results_df:
            if str(column).startswith("Unnamed"):
                results_df = results_df.drop(columns=column)

        results = {
            f"{row}{col}": values[col]
            for row, values in results_df.iterrows()
            for col in results_df.columns
        }

        a1_value = str(
            assert_not_none(
                results.get("A1"),
                msg=f"Unable to find first position of analysis result '{analysis_parameter}'.",
            )
        )

        # if first value is not a valid float value the results are not useful
        if try_float_or_none(a1_value) is None:
            return None

        return AnalysisResult(
            analysis_parameter=analysis_parameter,
            results=results,
        )

    def get_result(self, well_position: str) -> str:
        return str(
            assert_not_none(
                self.results.get(str(well_position)),
                msg=f"Unable to get well at position '{well_position}' from analysis result '{self.analysis_parameter}'.",
            )
        )

    def get_image_feature_result(self, well_position: str) -> float:
        return try_float(
            self.get_result(well_position),
            f"analysis result '{self.analysis_parameter}' at '{well_position}'",
        )


@dataclass(frozen=True)
class MeasurementInfo:
    instrument_serial_number: str
    measurement_time: str
    protocol_signature: str
    measurement_signature: str

    @staticmethod
    def create(elements: dict[str, str]) -> MeasurementInfo:
        instrument_serial_number = assert_not_none(
            elements.get("Instrument Serial Number"),
            msg="Unable to find Instrument Serial Number in Measurement Information section.",
        )

        measurement_time = assert_not_none(
            elements.get("Measurement Started"),
            msg="Unable to find Measurement time in Measurement Information section.",
        )

        protocol_signature = assert_not_none(
            elements.get("Protocol Signature"),
            msg="Unable to find Protocol Signature in Measurement Information section.",
        )

        measurement_signature = assert_not_none(
            elements.get("Measurement Signature"),
            msg="Unable to find Measurement Signature in Measurement Information section.",
        )

        return MeasurementInfo(
            instrument_serial_number,
            measurement_time,
            protocol_signature,
            measurement_signature,
        )


@dataclass(frozen=True)
class Platemap:
    data: dict[str, str]

    def get_well_value(self, well_position: str) -> str:
        return str(
            assert_not_none(
                self.data.get(well_position),
                msg=f"Unable to get well at position '{well_position}' from platemap section.",
            )
        )

    def get_sample_role_type(self, well_position: str) -> str | None:
        raw_value = self.get_well_value(well_position)
        if raw_value == "-":
            return None

        value = assert_not_none(
            re.match(r"^([A-Z]+)\d+$", raw_value),
            msg=f"Unable to understand platemap value '{raw_value}' for well position '{well_position}'.",
        ).group(1)

        return assert_not_none(
            PLATEMAP_TO_SAMPLE_ROLE_TYPE.get(value),
            msg=f"Unable to find sample role type for well position '{well_position}'.",
        )


@dataclass(frozen=True)
class MeasurementElement:
    title: str
    value: str


@dataclass(frozen=True)
class Channel:
    name: str
    fluorescent_tag: str | None
    transmitted_light: TransmittedLightSetting | None
    excitation_wavelength: float
    illumination: float
    exposure_duration: float
    additional_focus_offset: float

    @staticmethod
    def check_element_title(element: MeasurementElement, expected_title: str) -> None:
        if element.title != expected_title:
            msg = f"Expected to get '{expected_title}' but '{element.title}' was found."
            raise AllotropeConversionError(msg)

    @staticmethod
    def create(
        name: MeasurementElement,
        excitation_wavelength: MeasurementElement,
        excitation_power: MeasurementElement,
        exposure_time: MeasurementElement,
        additional_focus_offset: MeasurementElement,
    ) -> Channel:
        Channel.check_element_title(name, "Channel")
        Channel.check_element_title(excitation_wavelength, "Excitation wavelength [nm]")
        Channel.check_element_title(excitation_power, "Excitation Power [%]")
        Channel.check_element_title(exposure_time, "Exposure Time [ms]")
        Channel.check_element_title(
            additional_focus_offset, "Additional Focus offset [mm]"
        )

        return Channel(
            name.value,
            fluorescent_tag=None if name.value == "BRIGHTFIELD" else name.value,
            transmitted_light=TRANSMITTED_LIGHT_CONVERSION.get(name.value),
            excitation_wavelength=try_float(
                excitation_wavelength.value.removesuffix("nm"), "excitation wavelength"
            ),
            illumination=try_float(excitation_power.value, "excitation power"),
            exposure_duration=try_float(exposure_time.value, "exposure time"),
            additional_focus_offset=try_float(
                additional_focus_offset.value, "additional focus offset"
            ),
        )


@dataclass(frozen=True)
class Measurements:
    channels: list[Channel]
    number_of_averages: float | None
    detector_distance: float | None
    scan_position: ScanPositionSettingPlateReader | None
    emission_wavelength: float | None
    excitation_wavelength: float | None
    focus_height: float | None

    @staticmethod
    def create_channels(elements: list[MeasurementElement]) -> list[Channel]:
        try:
            return [
                Channel.create(
                    name=elements[idx],
                    excitation_wavelength=elements[idx + 1],
                    excitation_power=elements[idx + 2],
                    exposure_time=elements[idx + 3],
                    additional_focus_offset=elements[idx + 4],
                )
                for idx, element in enumerate(elements)
                if element.title == "Channel"
            ]
        except IndexError as e:
            msg = "Unable to get channel elements from Measurement section."
            raise AllotropeConversionError(msg) from e

    @staticmethod
    def try_element_or_none(
        elements: list[MeasurementElement], title: str
    ) -> MeasurementElement | None:
        for element in elements:
            if element.title == title:
                return element
        return None

    @staticmethod
    def get_element_float_value_or_none(
        elements: list[MeasurementElement], title: str
    ) -> float | None:
        element = Measurements.try_element_or_none(elements, title)
        if element is None:
            return None
        return try_float_or_none(element.value)


@dataclass(frozen=True)
class Data:
    version: str
    background_info: BackgroundInfo
    results: Results
    analysis_results: list[AnalysisResult]
    measurement_info: MeasurementInfo
    platemap: Platemap
    measurements: Measurements

    def iter_wells(self) -> Iterator[str]:
        yield from self.results.data

    def get_well_float_value(self, well_position: str) -> float:
        return self.results.get_well_float_value(well_position)

    def get_well_str_value(self, well_position: str) -> str:
        return self.results.get_well_str_value(well_position)

    def get_platemap_well_value(self, well_position: str) -> str:
        return self.platemap.get_well_value(well_position)

    def get_sample_role_type(self, well_position: str) -> str | None:
        return self.platemap.get_sample_role_type(well_position)

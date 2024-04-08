from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import logging
import re
from typing import Optional

import pandas as pd

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
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


@dataclass(frozen=True)
class WellPosition:
    column: str
    row: str

    def __repr__(self) -> str:
        return self.row + self.column


@dataclass
class BackgroundInfo:
    experiment_type: str


@dataclass(frozen=True)
class Results:
    barcode: str
    results: pd.DataFrame

    def iter_wells(self) -> Iterator[WellPosition]:
        for row, row_series in self.results.iterrows():
            for column in row_series.index:
                yield WellPosition(column=str(column), row=str(row))

    def get_plate_well_dimentions(self) -> tuple[int, int]:
        return self.results.shape

    def get_plate_well_count(self) -> int:
        n_rows, n_columns = self.get_plate_well_dimentions()
        return n_rows * n_columns

    def get_well_float_value(self, well_position: WellPosition) -> float:
        return try_float(
            self.get_well_str_value(well_position),
            f"result well at '{well_position}'",
        )

    def get_well_str_value(self, well_position: WellPosition) -> str:
        try:
            return str(self.results.loc[well_position.row, well_position.column])
        except KeyError as e:
            error = f"Unable to get well at position '{well_position}' from results section."
            raise AllotropeConversionError(error) from e


@dataclass(frozen=True)
class AnalysisResult:
    analysis_parameter: str
    results: pd.DataFrame

    @staticmethod
    def create(reader: CsvReader) -> Optional[AnalysisResult]:
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
            results = assert_not_none(
                reader.pop_csv_block_as_df(header=0, index_col=0),
                msg="Unable to find results table.",
            )
        except AllotropeConversionError:
            logging.warning(
                f"Unable to read analysis result '{analysis_parameter}'. Ignoring"
            )
            return None

        for column in results:
            if str(column).startswith("Unnamed"):
                results = results.drop(columns=column)

        try:
            a1_str_value = str(results.iloc[0, 0])
        except IndexError as e:
            error = f"Unable to find first position of analysis result '{analysis_parameter}'."
            raise AllotropeConversionError(error) from e

        if try_float_or_none(a1_str_value) is None:
            return None

        return AnalysisResult(
            analysis_parameter=analysis_parameter,
            results=results,
        )

    def get_image_feature_name(self) -> str:
        return self.analysis_parameter

    def get_result(self, well_position: WellPosition) -> str:
        try:
            return str(self.results.loc[well_position.row, well_position.column])
        except KeyError as e:
            error = f"Unable to get well at position '{well_position}' from analysis result '{self.analysis_parameter}'."
            raise AllotropeConversionError(error) from e

    def get_image_feature_result(self, well_position: WellPosition) -> float:
        return try_float(
            self.get_result(well_position),
            f"analysis result '{self.analysis_parameter}' at '{well_position}'",
        )


@dataclass(frozen=True)
class MeasurementInfo:
    elements: dict[str, str]

    def get_instrument_serial_number(self) -> str:
        return assert_not_none(
            self.elements.get("Instrument Serial Number"),
            msg="Unable to find Instrument Serial Number in Measurement Information section.",
        )

    def get_measurement_time(self) -> str:
        return assert_not_none(
            self.elements.get("Measurement Started"),
            msg="Unable to find Measurement time in Measurement Information section.",
        )

    def get_protocol_signature(self) -> str:
        return assert_not_none(
            self.elements.get("Protocol Signature"),
            msg="Unable to find Protocol Signature in Measurement Information section.",
        )

    def get_measurement_signature(self) -> str:
        return assert_not_none(
            self.elements.get("Measurement Signature"),
            msg="Unable to find Measurement Signature in Measurement Information section.",
        )


@dataclass(frozen=True)
class PlateType:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> PlateType:
        assert_not_none(
            reader.drop_until_inclusive("^Plate Type"),
            msg="Unable to find Plate Type section.",
        )
        reader.drop_until("^Platemap")
        return PlateType({})


@dataclass(frozen=True)
class Platemap:
    data: pd.DataFrame

    def get_well_value(self, well_position: WellPosition) -> str:
        try:
            return str(self.data.loc[well_position.row, well_position.column])
        except KeyError as e:
            error = f"Unable to get well at position '{well_position}' from platemap section."
            raise AllotropeConversionError(error) from e

    def get_sample_role_type(self, well_position: WellPosition) -> Optional[str]:
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
    excitation_wavelength: float
    excitation_power: float
    exposure_time: float
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
            try_float(
                excitation_wavelength.value.removesuffix("nm"), "excitation wavelength"
            ),
            try_float(excitation_power.value, "excitation power"),
            try_float(exposure_time.value, "exposure time"),
            try_float(additional_focus_offset.value, "additional focus offset"),
        )

    def get_exposure_duration(self) -> float:
        return self.exposure_time

    def get_illumination(self) -> float:
        return self.excitation_power

    def get_transmitted_light(self) -> Optional[TransmittedLightSetting]:
        return TRANSMITTED_LIGHT_CONVERSION.get(self.name)

    def get_fluorescent_tag(self) -> Optional[str]:
        return None if self.name == "BRIGHTFIELD" else self.name


@dataclass(frozen=True)
class Measurements:
    elements: list[MeasurementElement]
    channels: list[Channel]
    number_of_flashes: str
    detector_distance: str
    position: str
    emission_wavelength: str
    excitation_wavelength: str
    focus_height: str

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

    def try_element_or_none(self, title: str) -> Optional[MeasurementElement]:
        for element in self.elements:
            if element.title == title:
                return element
        return None

    def get_number_of_averages(self) -> Optional[float]:
        number_of_flashes = self.try_element_or_none(self.number_of_flashes)
        if number_of_flashes is None:
            return None
        return try_float(number_of_flashes.value, self.number_of_flashes)

    def get_detector_distance(self) -> Optional[float]:
        detector_distance = self.try_element_or_none(self.detector_distance)
        if detector_distance is None:
            return None
        return try_float(detector_distance.value, self.detector_distance)

    def get_scan_position(self) -> Optional[ScanPositionSettingPlateReader]:
        position = self.try_element_or_none(self.position)
        if position is None:
            return None

        return assert_not_none(
            SCAN_POSITION_CONVERSION.get(position.value),
            msg=f"'{position.value}' is not a valid scan position, expected TOP or BOTTOM.",
        )

    def get_emission_wavelength(self) -> Optional[float]:
        emission_wavelength = self.try_element_or_none(self.emission_wavelength)
        if emission_wavelength is None:
            return None
        return try_float(emission_wavelength.value, self.emission_wavelength)

    def get_excitation_wavelength(self) -> Optional[float]:
        excitation_wavelength = self.try_element_or_none(self.excitation_wavelength)
        if excitation_wavelength is None:
            return None
        return try_float(
            excitation_wavelength.value.removesuffix("nm"), self.excitation_wavelength
        )

    def get_focus_height(self) -> Optional[float]:
        focus_height = self.try_element_or_none(self.focus_height)
        if focus_height is None:
            return None
        return try_float(focus_height.value, self.focus_height)


@dataclass(frozen=True)
class Data:
    version: str
    background_info: BackgroundInfo
    results: Results
    analysis_results: list[AnalysisResult]
    measurement_info: MeasurementInfo
    plate_type: PlateType
    platemap: Platemap
    measurements: Measurements

    def iter_wells(self) -> Iterator[WellPosition]:
        yield from self.results.iter_wells()

    def get_plate_well_count(self) -> int:
        return self.results.get_plate_well_count()

    def get_well_float_value(self, well_position: WellPosition) -> float:
        return self.results.get_well_float_value(well_position)

    def get_well_str_value(self, well_position: WellPosition) -> str:
        return self.results.get_well_str_value(well_position)

    def get_well_plate_identifier(self) -> str:
        return self.results.barcode

    def get_platemap_well_value(self, well_position: WellPosition) -> str:
        return self.platemap.get_well_value(well_position)

    def get_sample_role_type(self, well_position: WellPosition) -> Optional[str]:
        return self.platemap.get_sample_role_type(well_position)

    def get_number_of_averages(self) -> Optional[float]:
        return self.measurements.get_number_of_averages()

    def get_detector_distance(self) -> Optional[float]:
        return self.measurements.get_detector_distance()

    def get_scan_position(self) -> Optional[ScanPositionSettingPlateReader]:
        return self.measurements.get_scan_position()

    def get_emission_wavelength(self) -> Optional[float]:
        return self.measurements.get_emission_wavelength()

    def get_excitation_wavelength(self) -> Optional[float]:
        return self.measurements.get_excitation_wavelength()

    def get_focus_height(self) -> Optional[float]:
        return self.measurements.get_focus_height()

    def get_equipment_serial_number(self) -> str:
        return self.measurement_info.get_instrument_serial_number()

    def get_measurement_time(self) -> str:
        return self.measurement_info.get_measurement_time()

    def get_analytical_method_id(self) -> str:
        return self.measurement_info.get_protocol_signature()

    def get_experimentl_data_id(self) -> str:
        return self.measurement_info.get_measurement_signature()

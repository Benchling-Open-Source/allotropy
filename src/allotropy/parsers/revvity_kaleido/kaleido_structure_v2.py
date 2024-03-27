from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

import pandas as pd

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ScanPositionSettingPlateReader,
    TransmittedLightSetting,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.revvity_kaleido.kaleido_common_structure import (
    PLATEMAP_TO_SAMPLE_ROLE_TYPE,
    SCAN_POSITION_CONVERTION,
    TRANSMITTED_LIGHT_CONVERTION,
    WellPosition,
)
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    AnalysisResult,
    BackgroundInfo,
    Data,
    PlateType,
    Results,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
)


def create_background_info(reader: CsvReader) -> BackgroundInfo:
    line = assert_not_none(
        reader.drop_until_inclusive("^Results for.(.+) 1"),
        msg="Unable to find background information.",
    )

    experiment_type = assert_not_none(
        re.match("^Results for.(.+) 1", line),
        msg="Unable to find experiment type from background information section.",
    ).group(1)

    return BackgroundInfo(experiment_type)


def create_results(reader: CsvReader) -> Results:
    barcode_line = assert_not_none(
        reader.drop_until_inclusive("^Barcode:(.+),"),
        msg="Unable to find background information.",
    )

    raw_barcode, *_ = barcode_line.split(",")
    barcode = raw_barcode.removeprefix("Barcode:")

    results = assert_not_none(
        reader.pop_csv_block_as_df(header=0, index_col=0),
        msg="Unable to find results table.",
    )

    for column in results:
        if str(column).startswith("Unnamed"):
            results = results.drop(columns=column)

    return Results(
        barcode=barcode,
        results=results,
    )


def create_analysis_results(reader: CsvReader) -> list[AnalysisResult]:
    section_title = assert_not_none(
        reader.drop_until("^Results for|^Measurement Basic Information"),
        msg="Unable to find Analysis Result or Measurement Basic Information section.",
    )

    if section_title.startswith("Measurement Basic Information"):
        return []

    reader.drop_until("^Barcode")

    analysis_results = []
    while reader.match("^Barcode"):
        analysis_result = AnalysisResult.create(reader)
        if analysis_result.is_valid_result():
            analysis_results.append(analysis_result)

    return analysis_results


@dataclass(frozen=True)
class MeasurementBasicInfo:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> MeasurementBasicInfo:
        assert_not_none(
            reader.drop_until_inclusive("^Measurement Basic Information"),
            msg="Unable to find Measurement Basic Information section.",
        )

        elements = {}
        for raw_line in reader.pop_until("^Plate Type"):
            if raw_line == "":
                continue

            key, _, value, *_ = raw_line.split(",")
            elements[key.rstrip(":")] = value

        return MeasurementBasicInfo(elements)

    def get_instrument_serial_number(self) -> str:
        return assert_not_none(
            self.elements.get("Instrument Serial Number"),
            msg="Unable to find Instrument Serial Number in Measurement Basic Information section.",
        )

    def get_measurement_time(self) -> str:
        return assert_not_none(
            self.elements.get("Measurement Started"),
            msg="Unable to find Measurement time in Measurement Basic Information section.",
        )

    def get_protocol_signature(self) -> str:
        return assert_not_none(
            self.elements.get("Protocol Signature"),
            msg="Unable to find Protocol Signature in Measurement Basic Information section.",
        )

    def get_measurement_signature(self) -> str:
        return assert_not_none(
            self.elements.get("Measurement Signature"),
            msg="Unable to find Measurement Signature in Measurement Basic Information section.",
        )


@dataclass(frozen=True)
class Platemap:
    data: pd.DataFrame

    @staticmethod
    def create(reader: CsvReader) -> Platemap:
        assert_not_none(
            reader.drop_until_inclusive("^Platemap"),
            msg="Unable to find Platemap section.",
        )

        assert_not_none(
            reader.pop_if_match("^Plate"),
            msg="Unable to find platemap start indicator.",
        )

        data = assert_not_none(
            reader.pop_csv_block_as_df(header=0, index_col=0),
            msg="Unable to find platemap information.",
        )

        return Platemap(data)

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
        return TRANSMITTED_LIGHT_CONVERTION.get(self.name)

    def get_fluorescent_tag(self) -> Optional[str]:
        return None if self.name == "BRIGHTFIELD" else self.name


@dataclass(frozen=True)
class Measurements:
    elements: list[MeasurementElement]
    channels: list[Channel]

    @staticmethod
    def create(reader: CsvReader) -> Measurements:
        assert_not_none(
            reader.drop_until_inclusive("^Measurements"),
            msg="Unable to find Measurements section.",
        )

        elements = []
        for raw_line in reader.pop_until("^Analysis"):
            if raw_line == "":
                continue

            key, _, _, _, value, *_ = raw_line.split(",")
            elements.append(
                MeasurementElement(title=key.rstrip(":"), value=value),
            )

        return Measurements(elements, channels=Measurements.create_channels(elements))

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
        number_of_flashes = self.try_element_or_none("Number of flashes")
        if number_of_flashes is None:
            return None
        return try_float(number_of_flashes.value, "number of flashes")

    def get_detector_distance(self) -> Optional[float]:
        detector_distance = self.try_element_or_none(
            "Distance between Plate and Detector [mm]"
        )
        if detector_distance is None:
            return None
        return try_float(detector_distance.value, "detector distance")

    def get_scan_position(self) -> Optional[ScanPositionSettingPlateReader]:
        position = self.try_element_or_none("Excitation / Emission")
        if position is None:
            return None

        return assert_not_none(
            SCAN_POSITION_CONVERTION.get(position.value),
            msg=f"'{position.value}' is not a valid scan position, expected TOP or BOTTOM.",
        )

    def get_emission_wavelength(self) -> Optional[float]:
        emission_wavelength = self.try_element_or_none("Emission wavelength [nm]")
        if emission_wavelength is None:
            return None
        return try_float(emission_wavelength.value, "emission wavelength")

    def get_excitation_wavelength(self) -> Optional[float]:
        excitation_wavelength = self.try_element_or_none("Excitation wavelength [nm]")
        if excitation_wavelength is None:
            return None
        return try_float(
            excitation_wavelength.value.removesuffix("nm"), "excitation wavelength"
        )

    def get_focus_height(self) -> Optional[float]:
        focus_height = self.try_element_or_none("Focus Height [µm]")
        if focus_height is None:
            return None
        return try_float(focus_height.value, "focus height")


@dataclass(frozen=True)
class DataV2(Data):
    measurement_basic_info: MeasurementBasicInfo
    platemap: Platemap
    measurements: Measurements

    @staticmethod
    def create(version: str, reader: CsvReader) -> DataV2:
        return DataV2(
            version=version,
            background_info=create_background_info(reader),
            results=create_results(reader),
            analysis_results=create_analysis_results(reader),
            measurement_basic_info=MeasurementBasicInfo.create(reader),
            plate_type=PlateType.create(reader),
            platemap=Platemap.create(reader),
            measurements=Measurements.create(reader),
        )

    def get_equipment_serial_number(self) -> str:
        return self.measurement_basic_info.get_instrument_serial_number()

    def get_measurement_time(self) -> str:
        return self.measurement_basic_info.get_measurement_time()

    def get_analytical_method_id(self) -> str:
        return self.measurement_basic_info.get_protocol_signature()

    def get_experimentl_data_id(self) -> str:
        return self.measurement_basic_info.get_measurement_signature()

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

    def get_channels(self) -> list[Channel]:
        return self.measurements.channels

from __future__ import annotations

from collections.abc import Iterator
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
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_float_or_none,
)


@dataclass(frozen=True)
class EnsightResults:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> EnsightResults:
        assert_not_none(
            reader.pop_if_match("^EnSight Results from"),
            msg="Unable to find EnSight section.",
        )

        elements = {}
        for raw_line in reader.pop_until("^Result for"):
            if raw_line == "":
                continue

            key, value, *_ = raw_line.split(",")
            elements[key.rstrip(":")] = value

        return EnsightResults(elements)


@dataclass(frozen=True)
class BackgroundInfo:
    experiment_type: str

    @staticmethod
    def create(reader: CsvReader) -> BackgroundInfo:
        line = assert_not_none(
            reader.drop_until_inclusive("^Result for"),
            msg="Unable to find background information.",
        )

        experiment_type = assert_not_none(
            re.match("^Result for.(.+) 1", line),
            msg="Unable to find experiment type from background information section.",
        ).group(1)

        return BackgroundInfo(experiment_type)


@dataclass(frozen=True)
class Results:
    barcode: str
    results: pd.DataFrame

    @staticmethod
    def create(reader: CsvReader) -> Results:
        assert_not_none(
            reader.pop_if_match("^Barcode"),
            msg="Unable to find barcode indicator.",
        )

        barcode, *_ = assert_not_none(
            reader.pop_if_match("^.+,"),
            msg="Unable to find barcode value.",
        ).split(",", maxsplit=1)

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
    def create(reader: CsvReader) -> AnalysisResult:
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

        results = assert_not_none(
            reader.pop_csv_block_as_df(header=0, index_col=0),
            msg="Unable to find results table.",
        )

        for column in results:
            if str(column).startswith("Unnamed"):
                results = results.drop(columns=column)

        return AnalysisResult(
            analysis_parameter=analysis_parameter,
            results=results,
        )

    def get_image_feature_name(self) -> str:
        return self.analysis_parameter

    def is_valid_result(self) -> bool:
        a1 = WellPosition(column="1", row="A")
        first_result = self.get_result(a1)
        return try_float_or_none(first_result) is not None

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


class AnalysisResultList:
    @staticmethod
    def create(reader: CsvReader) -> list[AnalysisResult]:
        section_title = assert_not_none(
            reader.drop_until("^Results for|^Measurement Information"),
            msg="Unable to find Analysis Result or Measurement Information section.",
        )

        if section_title.startswith("Measurement Information"):
            return []

        reader.drop_until("^Barcode")

        analysis_results = []
        while reader.match("^Barcode"):
            analysis_result = AnalysisResult.create(reader)
            if analysis_result.is_valid_result():
                analysis_results.append(analysis_result)

        return analysis_results


@dataclass(frozen=True)
class MeasurementInfo:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> MeasurementInfo:
        assert_not_none(
            reader.drop_until_inclusive("^Measurement Information"),
            msg="Unable to find Measurement Information section.",
        )

        elements = {}
        for raw_line in reader.pop_until("^Instrument Information"):
            if raw_line == "":
                continue

            key, _, value, *_ = raw_line.split(",")
            elements[key.rstrip(":")] = value

        return MeasurementInfo(elements)

    def get_measurement_time(self) -> str:
        return assert_not_none(
            self.elements.get("Measurement Started"),
            msg="Unable to find Measurement time in Measurement Basic Information section.",
        )

    def get_measurement_signature(self) -> str:
        return assert_not_none(
            self.elements.get("Measurement Signature"),
            msg="Unable to find Measurement Signature in Measurement Information section",
        )


@dataclass(frozen=True)
class InstrumentInfo:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> InstrumentInfo:
        assert_not_none(
            reader.drop_until_inclusive("^Instrument Information"),
            msg="Unable to find Instrument Information section.",
        )

        elements = {}
        for raw_line in reader.pop_until("^Protocol Information"):
            if raw_line == "":
                continue

            key, _, value, *_ = raw_line.split(",")
            elements[key.rstrip(":")] = value

        return InstrumentInfo(elements)

    def get_instrument_serial_number(self) -> str:
        return assert_not_none(
            self.elements.get("Instrument Serial Number"),
            msg="Unable to find Instrument Serial Number in Instrument Information section.",
        )


@dataclass(frozen=True)
class ProtocolInfo:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> ProtocolInfo:
        assert_not_none(
            reader.drop_until_inclusive("^Protocol Information"),
            msg="Unable to find Protocol Information section.",
        )

        elements = {}
        for raw_line in reader.pop_until("^Plate Type Information"):
            if raw_line == "":
                continue

            key, _, value, *_ = raw_line.split(",")
            elements[key.rstrip(":")] = value

        return ProtocolInfo(elements)

    def get_protocol_signature(self) -> str:
        return assert_not_none(
            self.elements.get("Protocol Signature"),
            msg="Unable to find Protocol Signature in Protocol Information section.",
        )


@dataclass(frozen=True)
class PlateTypeInfo:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> PlateTypeInfo:
        assert_not_none(
            reader.drop_until_inclusive("^Plate Type Information"),
            msg="Unable to find Plate Type Information section.",
        )

        elements: dict[str, str] = {}
        # for raw_line in reader.pop_until("^Platemap"):
        #     if raw_line == "":
        #         continue

        #     key, _, value, *_ = raw_line.split(",")
        #     elements[key.rstrip(":")] = value

        reader.drop_until("^Platemap")

        return PlateTypeInfo(elements)


@dataclass(frozen=True)
class Platemap:
    data: pd.DataFrame

    @staticmethod
    def create(reader: CsvReader) -> Platemap:
        assert_not_none(
            reader.drop_until_inclusive("^Platemap"),
            msg="Unable to find Platemap section.",
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
class DetailsMeasurementSequence:
    elements: list[MeasurementElement]
    channels: list[Channel]

    @staticmethod
    def create(reader: CsvReader) -> DetailsMeasurementSequence:
        assert_not_none(
            reader.drop_until_inclusive("^Details of Measurement Sequence"),
            msg="Unable to find Details of Measurement Sequence section.",
        )

        elements = []
        for raw_line in reader.pop_until("^Post Processing Sequence"):
            if raw_line == "":
                continue

            key, _, _, value, *_ = raw_line.split(",")
            elements.append(
                MeasurementElement(title=key.rstrip(":"), value=value),
            )

        return DetailsMeasurementSequence(
            elements,
            channels=DetailsMeasurementSequence.create_channels(elements),
        )

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
        number_of_flashes = self.try_element_or_none("Number of Flashes")
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
        emission_wavelength = self.try_element_or_none("Emission Wavelength [nm]")
        if emission_wavelength is None:
            return None
        return try_float(emission_wavelength.value, "emission wavelength")

    def get_excitation_wavelength(self) -> Optional[float]:
        excitation_wavelength = self.try_element_or_none("Excitation Wavelength [nm]")
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
class DataV3:
    version: str
    ensight_results: EnsightResults
    background_info: BackgroundInfo
    results: Results
    analysis_results: list[AnalysisResult]
    measurement_info: MeasurementInfo
    instrument_info: InstrumentInfo
    protocol_info: ProtocolInfo
    plate_type_info: PlateTypeInfo
    platemap: Platemap
    details_measurement_sequence: DetailsMeasurementSequence

    @staticmethod
    def create(version: str, reader: CsvReader) -> DataV3:
        return DataV3(
            version=version,
            ensight_results=EnsightResults.create(reader),
            background_info=BackgroundInfo.create(reader),
            results=Results.create(reader),
            analysis_results=AnalysisResultList.create(reader),
            measurement_info=MeasurementInfo.create(reader),
            instrument_info=InstrumentInfo.create(reader),
            protocol_info=ProtocolInfo.create(reader),
            plate_type_info=PlateTypeInfo.create(reader),
            platemap=Platemap.create(reader),
            details_measurement_sequence=DetailsMeasurementSequence.create(reader),
        )

    def get_equipment_serial_number(self) -> str:
        return self.instrument_info.get_instrument_serial_number()

    def iter_wells(self) -> Iterator[WellPosition]:
        yield from self.results.iter_wells()

    def get_plate_well_count(self) -> int:
        return self.results.get_plate_well_count()

    def get_measurement_time(self) -> str:
        return self.measurement_info.get_measurement_time()

    def get_experiment_type(self) -> str:
        return self.background_info.experiment_type

    def get_analytical_method_id(self) -> str:
        return self.protocol_info.get_protocol_signature()

    def get_experimentl_data_id(self) -> str:
        return self.measurement_info.get_measurement_signature()

    def get_well_float_value(self, well_position: WellPosition) -> float:
        return self.results.get_well_float_value(well_position)

    def get_well_str_value(self, well_position: WellPosition) -> str:
        return self.results.get_well_str_value(well_position)

    def get_platemap_well_value(self, well_position: WellPosition) -> str:
        return self.platemap.get_well_value(well_position)

    def get_well_plate_identifier(self) -> str:
        return self.results.barcode

    def get_sample_role_type(self, well_position: WellPosition) -> Optional[str]:
        return self.platemap.get_sample_role_type(well_position)

    def get_number_of_averages(self) -> Optional[float]:
        return self.details_measurement_sequence.get_number_of_averages()

    def get_detector_distance(self) -> Optional[float]:
        return self.details_measurement_sequence.get_detector_distance()

    def get_scan_position(self) -> Optional[ScanPositionSettingPlateReader]:
        return self.details_measurement_sequence.get_scan_position()

    def get_emission_wavelength(self) -> Optional[float]:
        return self.details_measurement_sequence.get_emission_wavelength()

    def get_excitation_wavelength(self) -> Optional[float]:
        return self.details_measurement_sequence.get_excitation_wavelength()

    def get_focus_height(self) -> Optional[float]:
        return self.details_measurement_sequence.get_focus_height()

    def get_channels(self) -> list[Channel]:
        return self.details_measurement_sequence.channels

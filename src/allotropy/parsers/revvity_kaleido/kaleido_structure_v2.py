from __future__ import annotations

from dataclasses import dataclass
import re

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    AnalysisResult,
    BackgroundInfo,
    Data,
    MeasurementElement,
    Measurements,
    Platemap,
    PlateType,
    Results,
)
from allotropy.parsers.utils.values import assert_not_none


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


def create_platemap(reader: CsvReader) -> Platemap:
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


def create_measurements(reader: CsvReader) -> Measurements:
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

    return Measurements(
        elements,
        channels=Measurements.create_channels(elements),
        number_of_flashes="Number of flashes",
        detector_distance="Distance between Plate and Detector [mm]",
        position="Excitation / Emission",
        emission_wavelength="Emission wavelength [nm]",
        excitation_wavelength="Excitation wavelength [nm]",
        focus_height="Focus Height [µm]",
    )


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
class DataV2(Data):
    measurement_basic_info: MeasurementBasicInfo

    @staticmethod
    def create(version: str, reader: CsvReader) -> DataV2:
        return DataV2(
            version=version,
            background_info=create_background_info(reader),
            results=create_results(reader),
            analysis_results=create_analysis_results(reader),
            measurement_basic_info=MeasurementBasicInfo.create(reader),
            plate_type=PlateType.create(reader),
            platemap=create_platemap(reader),
            measurements=create_measurements(reader),
        )

    def get_equipment_serial_number(self) -> str:
        return self.measurement_basic_info.get_instrument_serial_number()

    def get_measurement_time(self) -> str:
        return self.measurement_basic_info.get_measurement_time()

    def get_analytical_method_id(self) -> str:
        return self.measurement_basic_info.get_protocol_signature()

    def get_experimentl_data_id(self) -> str:
        return self.measurement_basic_info.get_measurement_signature()

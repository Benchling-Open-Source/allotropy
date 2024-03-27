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
        reader.drop_until_inclusive("^Result for.(.+) 1"),
        msg="Unable to find background information.",
    )

    experiment_type = assert_not_none(
        re.match("^Result for.(.+) 1", line),
        msg="Unable to find experiment type from background information section.",
    ).group(1)

    return BackgroundInfo(experiment_type)


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


def create_results(reader: CsvReader) -> Results:
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


def create_analysis_results(reader: CsvReader) -> list[AnalysisResult]:
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


def create_platemap(reader: CsvReader) -> Platemap:
    assert_not_none(
        reader.drop_until_inclusive("^Platemap"),
        msg="Unable to find Platemap section.",
    )

    data = assert_not_none(
        reader.pop_csv_block_as_df(header=0, index_col=0),
        msg="Unable to find platemap information.",
    )

    return Platemap(data)


def create_measurements(reader: CsvReader) -> Measurements:
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

    return Measurements(
        elements,
        channels=Measurements.create_channels(elements),
        number_of_flashes="Number of Flashes",
        detector_distance="Distance between Plate and Detector [mm]",
        position="Excitation / Emission",
        emission_wavelength="Emission Wavelength [nm]",
        excitation_wavelength="Excitation Wavelength [nm]",
        focus_height="Focus Height [µm]",
    )


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
class DataV3(Data):
    ensight_results: EnsightResults
    measurement_info: MeasurementInfo
    instrument_info: InstrumentInfo
    protocol_info: ProtocolInfo

    @staticmethod
    def create(version: str, reader: CsvReader) -> DataV3:
        return DataV3(
            version=version,
            ensight_results=EnsightResults.create(reader),
            background_info=create_background_info(reader),
            results=create_results(reader),
            analysis_results=create_analysis_results(reader),
            measurement_info=MeasurementInfo.create(reader),
            instrument_info=InstrumentInfo.create(reader),
            protocol_info=ProtocolInfo.create(reader),
            plate_type=PlateType.create(reader),
            platemap=create_platemap(reader),
            measurements=create_measurements(reader),
        )

    def get_equipment_serial_number(self) -> str:
        return self.instrument_info.get_instrument_serial_number()

    def get_measurement_time(self) -> str:
        return self.measurement_info.get_measurement_time()

    def get_analytical_method_id(self) -> str:
        return self.protocol_info.get_protocol_signature()

    def get_experimentl_data_id(self) -> str:
        return self.measurement_info.get_measurement_signature()

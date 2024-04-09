import re

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    AnalysisResult,
    BackgroundInfo,
    Data,
    MeasurementElement,
    MeasurementInfo,
    Measurements,
    Platemap,
    PlateType,
    Results,
)
from allotropy.parsers.utils.values import assert_not_none


def create_background_info(reader: CsvReader) -> BackgroundInfo:
    assert_not_none(
        reader.pop_if_match("^EnSight Results from"),
        msg="Unable to find EnSight section.",
    )

    reader.drop_until("^Result for")

    line = assert_not_none(
        reader.drop_until_inclusive("^Result for.(.+) 1"),
        msg="Unable to find background information.",
    )

    experiment_type = assert_not_none(
        re.match("^Result for.(.+) 1", line),
        msg="Unable to find experiment type from background information section.",
    ).group(1)

    return BackgroundInfo(experiment_type)


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
        data={
            f"{row}{col}": values[col]
            for row, values in results.iterrows()
            for col in results.columns
        },
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
        if analysis_result := AnalysisResult.create(reader):
            analysis_results.append(analysis_result)

    return analysis_results


def create_measurement_info(reader: CsvReader) -> MeasurementInfo:
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

    assert_not_none(
        reader.drop_until_inclusive("^Instrument Information"),
        msg="Unable to find Instrument Information section.",
    )

    for raw_line in reader.pop_until("^Protocol Information"):
        if raw_line == "":
            continue

        key, _, value, *_ = raw_line.split(",")
        elements[key.rstrip(":")] = value

    assert_not_none(
        reader.drop_until_inclusive("^Protocol Information"),
        msg="Unable to find Protocol Information section.",
    )

    for raw_line in reader.pop_until("^Plate Type Information"):
        if raw_line == "":
            continue

        key, _, value, *_ = raw_line.split(",")
        elements[key.rstrip(":")] = value

    return MeasurementInfo(
        instrument_serial_number=MeasurementInfo.get_instrument_serial_number(elements),
        measurement_time=MeasurementInfo.get_measurement_time(elements),
        protocol_signature=MeasurementInfo.get_protocol_signature(elements),
        measurement_signature=MeasurementInfo.get_measurement_signature(elements),
    )


def create_platemap(reader: CsvReader) -> Platemap:
    assert_not_none(
        reader.drop_until_inclusive("^Platemap"),
        msg="Unable to find Platemap section.",
    )

    data = assert_not_none(
        reader.pop_csv_block_as_df(header=0, index_col=0),
        msg="Unable to find platemap information.",
    )

    return Platemap(
        data={
            f"{row}{col}": values[col]
            for row, values in data.iterrows()
            for col in data.columns
        }
    )


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


def create_data_v3(version: str, reader: CsvReader) -> Data:
    return Data(
        version=version,
        background_info=create_background_info(reader),
        results=create_results(reader),
        analysis_results=create_analysis_results(reader),
        measurement_info=create_measurement_info(reader),
        plate_type=PlateType.create(reader),
        platemap=create_platemap(reader),
        measurements=create_measurements(reader),
    )

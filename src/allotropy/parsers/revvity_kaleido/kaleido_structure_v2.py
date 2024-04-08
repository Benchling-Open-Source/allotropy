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
        results={
            f"{row}{col}": values[col]
            for row, values in results.iterrows()
            for col in results.columns
        },
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
        if analysis_result := AnalysisResult.create(reader):
            analysis_results.append(analysis_result)

    return analysis_results


def create_measurement_info(reader: CsvReader) -> MeasurementInfo:
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

    return MeasurementInfo(elements)


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

    return Platemap(
        data={
            f"{row}{col}": values[col]
            for row, values in data.iterrows()
            for col in data.columns
        }
    )


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


def create_data_v2(version: str, reader: CsvReader) -> Data:
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

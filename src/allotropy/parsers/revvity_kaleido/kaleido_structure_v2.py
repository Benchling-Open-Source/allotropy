import re

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.revvity_kaleido import constants
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    AnalysisResult,
    BackgroundInfo,
    Data,
    MeasurementElement,
    MeasurementInfo,
    Measurements,
    Platemap,
    Results,
)
from allotropy.parsers.utils.pandas import df_to_series_data
from allotropy.parsers.utils.values import assert_not_none, try_float_or_none


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
    barcode = raw_barcode.removeprefix("Barcode:").strip()

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
            f"{row}{col}": str(values[col])
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

    return MeasurementInfo.create(elements)


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

    lines = list(reader.pop_until("^Analysis"))
    df = reader.lines_as_df(lines, index_col=0, names=range(7)).T.dropna(how="all")
    data = df_to_series_data(df, index=0)

    scan_position = data.get(str, "Excitation / Emission")
    excitation_wavelength = data.get(str, "Excitation wavelength [nm]")

    print("!!!")
    print(data.series)
    return Measurements(
        channels=Measurements.create_channels(data),
        number_of_averages=data.get(float, "Number of flashes"),
        detector_distance=data.get(float, "Distance between Plate and Detector [mm]"),
        scan_position=(
            None
            if scan_position is None
            else assert_not_none(
                constants.SCAN_POSITION_CONVERSION.get(scan_position),
                msg=f"'{scan_position}' is not a valid scan position, expected TOP or BOTTOM.",
            )
        ),
        emission_wavelength=data.get(float, "Emission wavelength [nm]"),
        excitation_wavelength=(
            None
            if excitation_wavelength is None
            else try_float_or_none(
                excitation_wavelength.removesuffix("nm")
            )
        ),
        focus_height=data.get(float, "Focus Height [µm]"),
    )


def create_data_v2(version: str, reader: CsvReader) -> Data:
    background_info = create_background_info(reader)
    results = create_results(reader)
    analysis_results = create_analysis_results(reader)
    measurement_info = create_measurement_info(reader)

    assert_not_none(
        reader.drop_until_inclusive("^Plate Type"),
        msg="Unable to find Plate Type section.",
    )
    reader.drop_until("^Platemap")

    platemap = create_platemap(reader)
    measurements = create_measurements(reader)

    return Data(
        version,
        background_info,
        results,
        analysis_results,
        measurement_info,
        platemap,
        measurements,
    )

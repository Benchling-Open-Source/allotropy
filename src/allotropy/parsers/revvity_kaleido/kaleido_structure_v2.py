from dataclasses import dataclass

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    AnalysisResult,
    BackgroundInfo,
    Data,
    MeasurementInfo,
    Measurements,
    Platemap,
    Results,
)
from allotropy.parsers.utils.values import assert_not_none


@dataclass(frozen=True)
class ResultsV2(Results):
    @classmethod
    def read_barcode(cls, reader: CsvReader) -> str:
        barcode_line = assert_not_none(
            reader.drop_until_inclusive("^Barcode:(.+),"),
            msg="Unable to find background information.",
        )

        raw_barcode, *_ = barcode_line.split(",")
        return raw_barcode.removeprefix("Barcode:").strip()


def create_data_v2(version: str, reader: CsvReader) -> Data:
    background_info = BackgroundInfo.create(reader)
    results = ResultsV2.create(reader)
    analysis_result = AnalysisResult.create_results(
        reader, "Measurement Basic Information"
    )
    measurement_info = MeasurementInfo.create(
        reader, "Measurement Basic Information", "Plate Type"
    )
    return Data(
        version,
        background_info,
        results,
        analysis_result,
        measurement_info,
        Platemap.create(reader),
        Measurements.create(reader, "Measurements", "Analysis", measurement_info),
    )

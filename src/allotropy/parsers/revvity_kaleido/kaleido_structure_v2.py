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
    return Data(
        version,
        BackgroundInfo.create(reader),
        ResultsV2.create(reader),
        AnalysisResult.create_results(reader, "Measurement Basic Information"),
        MeasurementInfo.create(reader, "Measurement Basic Information", "Plate Type"),
        Platemap.create(reader),
        Measurements.create(reader, "Measurements", "Analysis"),
    )

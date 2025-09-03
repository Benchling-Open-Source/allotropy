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
class ResultsV3(Results):
    @classmethod
    def read_barcode(cls, reader: CsvReader) -> str:
        assert_not_none(
            reader.pop_if_match("^Barcode"),
            msg="Unable to find barcode indicator.",
        )

        raw_barcode, *_ = assert_not_none(
            reader.pop_if_match("^.+,"),
            msg="Unable to find barcode value.",
        ).split(",", maxsplit=1)
        return raw_barcode.strip()


def create_data_v3(version: str, reader: CsvReader) -> Data:
    background_info = BackgroundInfo.create(reader)
    results = ResultsV3.create(reader)
    analysis_result = AnalysisResult.create_results(reader, "Measurement Information")
    measurement_info = MeasurementInfo.create(
        reader, "Measurement Information", "Plate Type Information"
    )
    return Data(
        version,
        background_info,
        results,
        analysis_result,
        measurement_info,
        Platemap.create(reader),
        Measurements.create(
            reader,
            "Details of Measurement Sequence",
            "Post Processing Sequence",
            measurement_info,
        ),
    )

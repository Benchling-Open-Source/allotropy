from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import assert_not_none


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
    info: str

    @staticmethod
    def create(reader: CsvReader) -> BackgroundInfo:
        line = assert_not_none(
            reader.drop_until_inclusive("^Result for"),
            msg="Unable to find background information.",
        )
        return BackgroundInfo(line)


@dataclass(frozen=True)
class Results:
    metadata: pd.DataFrame
    results: pd.DataFrame

    @staticmethod
    def create(reader: CsvReader) -> Results:
        metadata = assert_not_none(
            reader.pop_csv_block_as_df(header=0),
            msg="Unable to find Result barcode information.",
        )

        results = assert_not_none(
            reader.pop_csv_block_as_df(header=0, index_col=0),
            msg="Unable to find results table.",
        )

        return Results(
            metadata=metadata,
            results=results,
        )


@dataclass(frozen=True)
class AnalysisResults:
    @staticmethod
    def create(reader: CsvReader) -> Optional[AnalysisResults]:
        section_title = assert_not_none(
            reader.drop_until("^Results for|^Measurement Information"),
            msg="Unable to find Analysis Result or Measurement Basic section.",
        )

        if section_title.startswith("Measurement Information"):
            return None

        return AnalysisResults()


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
class DataV3:
    ensight_results: EnsightResults
    background_info: BackgroundInfo
    results: Results
    analysis_results: Optional[AnalysisResults]
    measurement_info: MeasurementInfo
    instrument_info: InstrumentInfo
    protocol_info: ProtocolInfo
    plate_type_info: PlateTypeInfo

    @staticmethod
    def create(reader: CsvReader) -> DataV3:
        return DataV3(
            ensight_results=EnsightResults.create(reader),
            background_info=BackgroundInfo.create(reader),
            results=Results.create(reader),
            analysis_results=AnalysisResults.create(reader),
            measurement_info=MeasurementInfo.create(reader),
            instrument_info=InstrumentInfo.create(reader),
            protocol_info=ProtocolInfo.create(reader),
            plate_type_info=PlateTypeInfo.create(reader),
        )

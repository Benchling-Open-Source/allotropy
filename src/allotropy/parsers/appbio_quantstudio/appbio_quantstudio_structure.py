# header
# sample setup
# raw data
# amplification data
# multicomponent data
# results
# melt curve raw data

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from io import StringIO
import re
from typing import Any, TypeVar

import numpy as np
import pandas as pd

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.allotrope.pandas_util import read_csv
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.calculated_data_documents.definition import Referenceable
from allotropy.parsers.utils.pandas import df_to_series_data, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_int

T = TypeVar("T")


def map_wells(map_func: Callable[..., T], data: pd.DataFrame) -> dict[int, T]:
    return {
        try_int(str(well_id), "well id"): map_func(well_data)
        for well_id, well_data in data.groupby("Well")
    }


@dataclass(frozen=True)
class Header:
    measurement_time: str
    plate_well_count: int | None
    experiment_type: ExperimentType
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    pcr_detection_chemistry: str
    passive_reference_dye_setting: str | None
    barcode: str | None
    analyst: str | None
    experimental_data_identifier: str | None

    @staticmethod
    def create(reader: LinesReader) -> Header:
        lines = [line.replace("*", "", 1) for line in reader.pop_until(r"^\[.+\]")]
        csv_stream = StringIO("\n".join(lines))
        raw_data = read_csv(csv_stream, header=None, sep="=", names=["index", "values"])
        series = pd.Series(raw_data["values"].values, index=raw_data["index"]).astype(
            str
        )
        series.index = series.index.str.strip()
        series = series.str.strip().replace("NA", None)

        data = SeriesData(series)

        experiments_type_options = {
            "Standard Curve": ExperimentType.standard_curve_qPCR_experiment,
            "Relative Standard Curve": ExperimentType.relative_standard_curve_qPCR_experiment,
            "Comparative Cт (ΔΔCт)": ExperimentType.comparative_CT_qPCR_experiment,
            "Melt Curve": ExperimentType.melt_curve_qPCR_experiment,
            "Genotyping": ExperimentType.genotyping_qPCR_experiment,
            "Presence/Absence": ExperimentType.presence_absence_qPCR_experiment,
        }

        plate_well_count_search = re.search("(96)|(384)", data[str, "Block Type"])

        return Header(
            measurement_time=data[str, "Experiment Run End Time"],
            plate_well_count=(
                None
                if plate_well_count_search is None
                else int(plate_well_count_search.group())
            ),
            experiment_type=assert_not_none(
                experiments_type_options.get(
                    data[str, "Experiment Type"],
                ),
                msg="Unable to find valid experiment type",
            ),
            device_identifier=(data.get(str, "Instrument Name", NOT_APPLICABLE)),
            model_number=data[str, "Instrument Type"],
            device_serial_number=data.get(
                str, "Instrument Serial Number", NOT_APPLICABLE
            ),
            measurement_method_identifier=data[str, "Quantification Cycle Method"],
            pcr_detection_chemistry=data[str, "Chemistry"],
            passive_reference_dye_setting=data.get(str, "Passive Reference"),
            barcode=data.get(str, "Experiment Barcode"),
            analyst=data.get(str, "Experiment User Name"),
            experimental_data_identifier=data.get(str, "Experiment Name"),
        )


@dataclass
class WellItem(Referenceable):
    identifier: int
    target_dna_description: str
    sample_identifier: str
    reporter_dye_setting: str | None = None
    position: str | None = None
    well_location_identifier: str | None = None
    quencher_dye_setting: str | None = None
    sample_role_type: str | None = None
    _result: Result | None = None

    @property
    def result(self) -> Result:
        return assert_not_none(self._result)

    @staticmethod
    def create_genotyping(data: SeriesData) -> tuple[WellItem, WellItem]:
        identifier = data[int, "Well"]
        snp_name = data[
            str, "SNP Assay Name", f"Unable to find snp name for well {identifier}"
        ]
        allele1 = data[
            str, "Allele1 Name", f"Unable to find allele 1 for well {identifier}"
        ]
        allele2 = data[
            str, "Allele2 Name", f"Unable to find allele 2 for well {identifier}"
        ]
        return (
            WellItem(
                uuid=random_uuid_str(),
                identifier=identifier,
                target_dna_description=f"{snp_name}-{allele1}",
                sample_identifier=data.get(str, "Sample Name", NOT_APPLICABLE),
                reporter_dye_setting=data.get(str, "Allele1 Reporter"),
                position=data.get(str, "Well Position", NOT_APPLICABLE),
                well_location_identifier=data.get(str, "Well Position"),
                quencher_dye_setting=data.get(str, "Quencher"),
                sample_role_type=data.get(str, "Task"),
            ),
            WellItem(
                uuid=random_uuid_str(),
                identifier=identifier,
                target_dna_description=f"{snp_name}-{allele2}",
                sample_identifier=data.get(str, "Sample Name", NOT_APPLICABLE),
                reporter_dye_setting=data.get(str, "Allele2 Reporter"),
                position=data.get(str, "Well Position", NOT_APPLICABLE),
                well_location_identifier=data.get(str, "Well Position"),
                quencher_dye_setting=data.get(str, "Quencher"),
                sample_role_type=data.get(str, "Task"),
            ),
        )

    @staticmethod
    def create_generic(data: SeriesData) -> WellItem:
        identifier = data[int, "Well"]
        return WellItem(
            uuid=random_uuid_str(),
            identifier=identifier,
            target_dna_description=data[
                str,
                "Target Name",
                f"Unable to find target dna description for well {identifier}",
            ],
            sample_identifier=data.get(str, "Sample Name", NOT_APPLICABLE),
            reporter_dye_setting=data.get(str, "Reporter"),
            position=data.get(str, "Well Position", NOT_APPLICABLE),
            well_location_identifier=data.get(str, "Well Position"),
            quencher_dye_setting=data.get(str, "Quencher"),
            sample_role_type=data.get(str, "Task"),
        )


@dataclass
class Well:
    identifier: int
    items: list[WellItem]

    @staticmethod
    def create_genotyping(series: pd.Series[Any]) -> Well:
        return Well(
            identifier=try_int(str(series.name), "well id"),
            items=list(WellItem.create_genotyping(SeriesData(series))),
        )

    @staticmethod
    def create_generic(well_data: pd.DataFrame) -> Well:
        return Well(
            identifier=try_int(str(well_data["Well"].iloc[0]), "well id"),
            items=[
                WellItem.create_generic(SeriesData(item_data))
                for _, item_data in well_data.iterrows()
            ],
        )

    @staticmethod
    def create(reader: LinesReader, experiment_type: ExperimentType) -> list[Well]:
        assert_not_none(
            reader.drop_until(r"^\[Sample Setup\]"),
            msg="Unable to find 'Sample Setup' section in file.",
        )

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        data = read_csv(csv_stream, sep="\t").replace(np.nan, None)

        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return list(data.apply(Well.create_genotyping, axis="columns"))  # type: ignore[call-overload]
        else:
            return list(
                map_wells(
                    Well.create_generic, data[data["Target Name"].notnull()]
                ).values()
            )


@dataclass(frozen=True)
class RawData:
    lines: list[str]

    @staticmethod
    def create(reader: LinesReader) -> RawData | None:
        if reader.match(r"^\[Raw Data\]"):
            reader.pop()  # remove title
            return RawData(lines=list(reader.pop_until(r"^\[.+\]")))
        return None


@dataclass(frozen=True)
class AmplificationData:
    total_cycle_number_setting: float
    cycle: list[float]
    rn: list[float | None]
    delta_rn: list[float | None]

    @staticmethod
    def create(reader: LinesReader) -> dict[int, dict[str, AmplificationData]]:
        assert_not_none(
            reader.drop_until(r"^\[Amplification Data\]"),
            msg="Unable to find 'Amplification Data' section in file.",
        )

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        data = read_csv(csv_stream, sep="\t", thousands=r",")

        def make_data(well_data: pd.DataFrame) -> dict[str, AmplificationData]:
            return {
                str(target_name): AmplificationData(
                    total_cycle_number_setting=float(target_data["Cycle"].max()),
                    cycle=target_data["Cycle"].tolist(),
                    rn=target_data["Rn"].tolist(),
                    delta_rn=target_data["Delta Rn"].tolist(),
                )
                for target_name, target_data in well_data.groupby("Target Name")
            }

        return map_wells(make_data, data)


@dataclass(frozen=True)
class MulticomponentData:
    cycle: list[float]
    columns: dict[str, list[float | None]]

    def get_column(self, name: str) -> list[float | None]:
        return assert_not_none(
            self.columns.get(name),
            msg=f"Unable to obtain '{name}' from multicomponent data.",
        )

    @staticmethod
    def create(reader: LinesReader) -> dict[int, MulticomponentData]:
        if not reader.match(r"^\[Multicomponent Data\]"):
            return {}
        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        data = read_csv(csv_stream, sep="\t", thousands=r",")

        def make_data(well_data: pd.Series[Any]) -> MulticomponentData:
            return MulticomponentData(
                cycle=well_data["Cycle"].tolist(),
                columns={
                    name: well_data[name].tolist()
                    for name in well_data
                    if name not in ["Well", "Cycle", "Well Position"]
                },
            )

        return map_wells(make_data, data)


@dataclass(frozen=True)
class ResultMetadata:
    reference_dna_description: str | None
    reference_sample_description: str | None

    @staticmethod
    def create(data: SeriesData, experiment_type: ExperimentType) -> ResultMetadata:
        if experiment_type not in [
            ExperimentType.comparative_CT_qPCR_experiment,
            ExperimentType.relative_standard_curve_qPCR_experiment,
        ]:
            return ResultMetadata(None, None)
        return ResultMetadata(
            reference_dna_description=data.get(
                str, "Endogenous Control", NOT_APPLICABLE
            ),
            reference_sample_description=data.get(
                str, "Reference Sample", NOT_APPLICABLE
            ),
        )


@dataclass(frozen=True)
class Result:
    cycle_threshold_value_setting: float
    cycle_threshold_result: float | None
    automatic_cycle_threshold_enabled_setting: bool | None
    automatic_baseline_determination_enabled_setting: bool | None
    normalized_reporter_result: float | None
    baseline_corrected_reporter_result: float | None
    genotyping_determination_result: str | None
    genotyping_determination_method_setting: float | None
    quantity: float | None
    quantity_mean: float | None
    quantity_sd: float | None
    ct_mean: float | None
    ct_sd: float | None
    delta_ct_mean: float | None
    delta_ct_se: float | None
    delta_delta_ct: float | None
    rq: float | None
    rq_min: float | None
    rq_max: float | None
    rn_mean: float | None
    rn_sd: float | None
    y_intercept: float | None
    r_squared: float | None
    slope: float | None
    efficiency: float | None

    @staticmethod
    def create(
        reader: LinesReader, experiment_type: ExperimentType
    ) -> tuple[dict[int, dict[str, Result]], ResultMetadata]:
        assert_not_none(
            reader.drop_until(r"^\[Results\]"),
            msg="Unable to find 'Results' section in file.",
        )

        reader.pop()  # remove title
        data_lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(data_lines))
        data = read_csv(csv_stream, sep="\t", thousands=r",").replace(np.nan, None)
        result = Result.create_results(data, experiment_type)

        reader.drop_empty()

        if reader.match(r"\[.+\]"):
            return result, ResultMetadata.create(
                SeriesData(pd.Series()), experiment_type
            )

        metadata_lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(metadata_lines))
        raw_data = read_csv(csv_stream, header=None, sep="=", names=["index", "values"])
        metadata = pd.Series(raw_data["values"].values, index=raw_data["index"])
        metadata.index = metadata.index.str.strip()

        reader.drop_empty()

        return result, ResultMetadata.create(
            SeriesData(metadata.str.strip()), experiment_type
        )

    @staticmethod
    def create_results(
        data: pd.DataFrame, experiment_type: ExperimentType
    ) -> dict[int, dict[str, Result]]:
        target_key = "Target Name"
        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            target_key = "SNP Assay Name"

        def make_results(well_data: pd.DataFrame) -> dict[str, Result]:
            return {
                target_dna_description: result
                for target_id, target_data in well_data.groupby(target_key)
                for target_dna_description, result in Result.create_result(
                    df_to_series_data(
                        target_data, msg="Unable to find parser result data"
                    ),
                    experiment_type,
                    str(target_id),
                ).items()
            }

        return map_wells(make_results, data)

    @staticmethod
    def create_result(
        data: SeriesData, experiment_type: ExperimentType, target_id: str
    ) -> dict[str, Result]:
        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            allele_prefixes = []
            for column in data.series.index:
                if match := re.match("(^\\w+) Ct$", column):
                    allele_prefixes.append(f"{match.groups()[0]} ")
        else:
            allele_prefixes = [""]

        return {
            f"{target_id}{f'-{allele_prefix}' if allele_prefix else ''}".replace(
                " ", ""
            ): Result(
                cycle_threshold_value_setting=data[
                    float, f"{allele_prefix}Ct Threshold"
                ],
                # TODO(nstender): really seems like this should be NaN if invalid value. Keeping to preserve tests.
                cycle_threshold_result=data.get(
                    float, [f"{allele_prefix}Ct", f"{allele_prefix}CT"]
                ),
                automatic_cycle_threshold_enabled_setting=data.get(
                    bool, f"{allele_prefix}Automatic Ct Threshold"
                ),
                automatic_baseline_determination_enabled_setting=data.get(
                    bool, f"{allele_prefix}Automatic Baseline"
                ),
                normalized_reporter_result=data.get(float, "Rn"),
                baseline_corrected_reporter_result=data.get(
                    float, f"{allele_prefix}Delta Rn"
                ),
                genotyping_determination_result=data.get(str, "Call"),
                genotyping_determination_method_setting=data.get(
                    float, "Threshold Value"
                ),
                quantity=data.get(float, "Quantity"),
                quantity_mean=data.get(float, "Quantity Mean"),
                quantity_sd=data.get(float, "Quantity SD"),
                ct_mean=data.get(float, "Ct Mean"),
                ct_sd=data.get(float, "Ct SD"),
                delta_ct_mean=data.get(float, "Delta Ct Mean"),
                delta_ct_se=data.get(float, "Delta Ct SE"),
                delta_delta_ct=data.get(float, "Delta Delta Ct"),
                rq=data.get(float, "RQ"),
                rq_min=data.get(float, "RQ Min"),
                rq_max=data.get(float, "RQ Max"),
                rn_mean=data.get(float, "Rn Mean"),
                rn_sd=data.get(float, "Rn SD"),
                y_intercept=data.get(float, "Y-Intercept"),
                r_squared=data.get(float, "R(superscript 2)"),
                slope=data.get(float, "Slope"),
                efficiency=data.get(float, "Efficiency"),
            )
            for allele_prefix in allele_prefixes
        }


@dataclass(frozen=True)
class MeltCurveRawData:
    reading: list[float]
    fluorescence: list[float | None]
    derivative: list[float | None]

    @staticmethod
    def create(reader: LinesReader) -> dict[int, MeltCurveRawData]:
        if not reader.match(r"^\[Melt Curve Raw Data\]"):
            return {}
        reader.pop()  # remove title
        lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(lines))
        data = read_csv(csv_stream, sep="\t", thousands=r",")

        def make_data(well_data: pd.Series[Any]) -> MeltCurveRawData:
            return MeltCurveRawData(
                reading=well_data["Reading"].tolist(),
                fluorescence=well_data["Fluorescence"].tolist(),
                derivative=well_data["Derivative"].tolist(),
            )

        return map_wells(make_data, data)

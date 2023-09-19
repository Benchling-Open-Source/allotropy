# header
# sample setup
# raw data
# amplification data
# multicomponent data
# results
# melt curve raw data

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re
from typing import Callable, Optional, TypeVar

import numpy as np
import pandas as pd

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils import assert_not_none, get_timestamp, try_float, try_int


def df_to_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(df.iloc[0], index=df.columns)


def get_str_from_series(
    series: pd.Series, key: str, default: Optional[str] = None
) -> Optional[str]:
    value = series.get(key)
    return str(value) if value not in ("", None) else default


def assert_str_from_series(series: pd.Series, key: str) -> str:
    return assert_not_none(get_str_from_series(series, key), key)


def bool_or_none(series: pd.Series, key: str) -> Optional[bool]:
    value = series.get(key)
    if isinstance(value, np.bool_):
        return bool(value)
    return None


T = TypeVar("T")


def map_well_data(
    data: pd.DataFrame, data_fn: Callable[[pd.DataFrame], T]
) -> dict[int, T]:
    return {
        assert_not_none(try_int(str(well_id))): data_fn(well_data)
        for well_id, well_data in data.groupby("Well")
    }


@dataclass
class Header:
    measurement_time: str
    plate_well_count: int
    experiment_type: ExperimentType
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    qpcr_detection_chemistry: str
    passive_reference_dye_setting: Optional[str]
    barcode: Optional[str]
    analyst: Optional[str]
    experimental_data_identifier: Optional[str]

    @staticmethod
    def create(reader: LinesReader) -> Header:
        lines = [line.replace("*", "", 1) for line in reader.pop_until(r"^\[.+\]")]
        csv_stream = StringIO("\n".join(lines))
        raw_data = pd.read_csv(
            csv_stream, header=None, sep="=", names=["index", "values"]
        )
        data = pd.Series(raw_data["values"].values, index=raw_data["index"])
        data.index = data.index.str.strip()
        data = data.str.strip().replace("NA", None)

        raw_time = assert_str_from_series(data, "Experiment Run End Time")
        time_regex = r"\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d (AM|PM)"
        regex_result = assert_not_none(
            re.search(time_regex, raw_time),
            f"Unable to understand time format {raw_time}",
        ).group()
        measurement_time = assert_not_none(
            get_timestamp(regex_result, "%Y-%m-%d %H:%M:%S %p")
        ).strftime("%Y-%m-%d %H:%M:%S")

        block_type = assert_str_from_series(data, "Block Type")
        number_match = assert_not_none(
            re.match("[1-9][0-9]+", block_type), msg="Block type missing number prefix"
        )
        plate_well_count = assert_not_none(try_int(number_match.group()))

        experiments_type_options = {
            "Standard Curve": ExperimentType.standard_curve_qPCR_experiment,
            "Relative Standard Curve": ExperimentType.relative_standard_curve_qPCR_experiment,
            "Comparative Cт (ΔΔCт)": ExperimentType.comparative_CT_qPCR_experiment,
            "Melt Curve": ExperimentType.melt_curve_qPCR_experiment,
            "Genotyping": ExperimentType.genotyping_qPCR_experiment,
            "Presence/Absence": ExperimentType.presence_absence_qPCR_experiment,
        }
        experiment_type = assert_not_none(
            experiments_type_options.get(
                assert_str_from_series(data, "Experiment Type"), None
            ),
            msg="Unable to get valid experiment type",
        )

        return Header(
            measurement_time=measurement_time,
            plate_well_count=plate_well_count,
            experiment_type=experiment_type,
            device_identifier=assert_str_from_series(data, "Instrument Name"),
            model_number=assert_str_from_series(data, "Instrument Type"),
            device_serial_number=assert_str_from_series(
                data, "Instrument Serial Number"
            ),
            measurement_method_identifier=assert_str_from_series(
                data, "Quantification Cycle Method"
            ),
            qpcr_detection_chemistry=assert_str_from_series(data, "Chemistry"),
            passive_reference_dye_setting=get_str_from_series(
                data, "Passive Reference"
            ),
            barcode=get_str_from_series(data, "Experiment Barcode"),
            analyst=get_str_from_series(data, "Experiment User Name"),
            experimental_data_identifier=get_str_from_series(data, "Experiment Name"),
        )


@dataclass
class WellItem:
    identifier: int
    target_dna_description: str
    sample_identifier: str
    reporter_dye_setting: Optional[str]
    position: Optional[str]
    well_location_identifier: Optional[str]
    quencher_dye_setting: Optional[str]
    sample_role_type: Optional[str]
    _amplification_data: Optional[AmplificationData] = None
    _result: Optional[Result] = None

    @staticmethod
    def create(
        data: pd.Series, target_dna_description: Optional[str] = None
    ) -> WellItem:
        return WellItem(
            identifier=assert_not_none(
                try_int(get_str_from_series(data, "Well")), "Well item id"
            ),
            target_dna_description=target_dna_description
            or assert_str_from_series(data, "Target Name"),
            sample_identifier=assert_str_from_series(data, "Sample Name"),
            reporter_dye_setting=get_str_from_series(data, "Reporter"),
            position=get_str_from_series(data, "Well Position", "UNDEFINED"),
            well_location_identifier=get_str_from_series(data, "Well Position"),
            quencher_dye_setting=get_str_from_series(data, "Quencher"),
            sample_role_type=get_str_from_series(data, "Task"),
        )

    @property
    def amplification_data(self) -> AmplificationData:
        return assert_not_none(self._amplification_data, "amplification data")

    @amplification_data.setter
    def amplification_data(self, amplification_data: AmplificationData) -> None:
        self._amplification_data = amplification_data

    @property
    def result(self) -> Result:
        return assert_not_none(self._result, "result data for well")

    @result.setter
    def result(self, result: Result) -> None:
        self._result = result


@dataclass
class Well:
    identifier: int
    items: list[WellItem]
    _multicomponent_data: Optional[MulticomponentData] = None
    _melt_curve_raw_data: Optional[MeltCurveRawData] = None

    @staticmethod
    def create(data: pd.DataFrame) -> list[Well]:
        return [
            Well(
                identifier=assert_not_none(try_int(str(well_id)), "Well id"),
                items=[
                    WellItem.create(item_data) for _, item_data in well_data.iterrows()
                ],
            )
            for well_id, well_data in data.groupby("Well")
        ]

    @property
    def multicomponent_data(self) -> Optional[MulticomponentData]:
        return self._multicomponent_data

    @multicomponent_data.setter
    def multicomponent_data(self, multicomponent_data: MulticomponentData) -> None:
        self._multicomponent_data = multicomponent_data

    @property
    def melt_curve_raw_data(self) -> Optional[MeltCurveRawData]:
        return self._melt_curve_raw_data

    @melt_curve_raw_data.setter
    def melt_curve_raw_data(self, melt_curve_raw_data: MeltCurveRawData) -> None:
        self._melt_curve_raw_data = melt_curve_raw_data


@dataclass
class GenotypingWell(Well):
    @staticmethod
    def create(data: pd.DataFrame) -> list[Well]:
        def get_well_items(well_data: pd.Series) -> list[WellItem]:
            snp_assay_name = assert_str_from_series(well_data, "SNP Assay Name")
            alleles = [
                assert_str_from_series(well_data, "Allele1 Name"),
                assert_str_from_series(well_data, "Allele2 Name"),
            ]
            return [
                WellItem.create(
                    well_data,
                    target_dna_description=f"{snp_assay_name}-{allele}",
                )
                for allele in alleles
            ]

        return [
            Well(
                identifier=assert_not_none(try_int(str(well_id)), "Well id"),
                items=get_well_items(well_data),
            )
            for well_id, well_data in data.iterrows()
        ]


def create_wells(reader: LinesReader, experiment_type: ExperimentType) -> list[Well]:
    raw_data = reader.pop_csv_block(r"^\[Sample Setup\]", sep="\t").replace(
        np.nan, None
    )
    data = raw_data[raw_data["Sample Name"].notnull()]

    if experiment_type == ExperimentType.genotyping_qPCR_experiment:
        return GenotypingWell.create(data)
    else:
        return Well.create(data)


@dataclass
class AmplificationData:
    total_cycle_number_setting: float
    cycle: list[float]
    rn: list[Optional[float]]
    delta_rn: list[Optional[float]]

    @staticmethod
    def create(reader: LinesReader) -> dict[int, dict[str, AmplificationData]]:
        data = reader.pop_csv_block(start_pattern=r"^\[Amplification Data\]", sep="\t")
        return map_well_data(
            data,
            lambda well_data: {
                str(target_name): AmplificationData(
                    total_cycle_number_setting=float(target_data["Cycle"].max()),
                    cycle=target_data["Cycle"].tolist(),
                    rn=target_data["Rn"].tolist(),
                    delta_rn=target_data["Delta Rn"].tolist(),
                )
                for target_name, target_data in well_data.groupby("Target Name")
            },
        )


@dataclass
class MulticomponentData:
    cycle: list[float]
    columns: dict[str, list[Optional[float]]]

    @staticmethod
    def create(reader: LinesReader) -> Optional[dict[int, MulticomponentData]]:
        if not reader.match(r"^\[Multicomponent Data\]"):
            return None
        data = reader.pop_csv_block(start_pattern=r"^\[Multicomponent Data\]", sep="\t")
        return map_well_data(
            data,
            lambda well_data: MulticomponentData(
                cycle=well_data["Cycle"].tolist(),
                columns={
                    name: well_data[name].str.replace(",", "").astype(float).tolist()  # type: ignore[misc]
                    for name in well_data
                    if name not in ["Well", "Cycle", "Well Position"]
                },
            ),
        )

    def get_column(self, name: str) -> list[Optional[float]]:
        return assert_not_none(
            self.columns.get(name), f"column {name} in multicomponent data"
        )


@dataclass
class Result:
    cycle_threshold_value_setting: float
    cycle_threshold_result: Optional[float]
    automatic_cycle_threshold_enabled_setting: Optional[bool]
    automatic_baseline_determination_enabled_setting: Optional[bool]
    normalized_reporter_result: Optional[float]
    baseline_corrected_reporter_result: Optional[float]
    genotyping_determination_result: Optional[str]
    genotyping_determination_method_setting: Optional[float]

    @staticmethod
    def create(series: pd.Series, allele: Optional[str] = None) -> Result:
        prefix = f"{allele} " if allele else ""
        return Result(
            cycle_threshold_value_setting=assert_not_none(
                try_float(get_str_from_series(series, f"{prefix}Ct Threshold")),
                "Ct Threshold",
            ),
            cycle_threshold_result=try_float(
                get_str_from_series(series, f"{prefix}Ct" if prefix else "CT")
            ),
            automatic_cycle_threshold_enabled_setting=bool_or_none(
                series, f"{prefix}Automatic Ct Threshold"
            ),
            automatic_baseline_determination_enabled_setting=bool_or_none(
                series, f"{prefix}Automatic Baseline"
            ),
            normalized_reporter_result=try_float(get_str_from_series(series, "Rn")),
            baseline_corrected_reporter_result=try_float(
                get_str_from_series(series, f"{prefix}Delta Rn")
            ),
            genotyping_determination_result=get_str_from_series(series, "Call"),
            genotyping_determination_method_setting=try_float(
                get_str_from_series(series, "Threshold Value")
            ),
        )


def get_results(
    reader: LinesReader, experiment_type: ExperimentType
) -> dict[int, dict[str, Result]]:
    data = reader.pop_csv_block(r"^\[Results\]", sep="\t")

    if experiment_type == ExperimentType.genotyping_qPCR_experiment:
        return map_well_data(
            data,
            lambda well_data: {
                f"{target_name}-{allele}": Result.create(
                    df_to_series(target_data), allele
                )
                for target_name, target_data in well_data.groupby("SNP Assay Name")
                for allele in {
                    col[:-13]
                    for col in target_data.columns
                    if re.match(r"\w+ Ct Threshold", col)
                }
            },
        )
    else:
        return map_well_data(
            data,
            lambda well_data: {
                str(target_name): Result.create(df_to_series(target_data))
                for target_name, target_data in well_data.groupby("Target Name")
            },
        )


@dataclass
class MeltCurveRawData:
    reading: list[float]
    fluorescence: list[Optional[float]]
    derivative: list[Optional[float]]

    @staticmethod
    def create(reader: LinesReader) -> Optional[dict[int, MeltCurveRawData]]:
        reader.drop_until(r"^\[Melt Curve Raw Data\]")
        if not reader.match(r"^\[Melt Curve Raw Data\]"):
            return None
        data = reader.pop_csv_block(r"^\[Melt Curve Raw Data\]", sep="\t")
        return map_well_data(
            data,
            lambda well_data: MeltCurveRawData(
                reading=well_data["Reading"].tolist(),
                fluorescence=well_data["Fluorescence"].tolist(),
                derivative=well_data["Derivative"].tolist(),
            ),
        )


@dataclass
class Data:
    header: Header
    wells: list[Well]

    @staticmethod
    def create(reader: LinesReader) -> Data:
        header = Header.create(reader)
        wells = create_wells(reader, header.experiment_type)

        reader.drop_sections(r"^\[Raw Data\]")

        amp_data = AmplificationData.create(reader)
        multi_data = MulticomponentData.create(reader)
        results_data = get_results(reader, header.experiment_type)
        melt_data = MeltCurveRawData.create(reader)
        for well in wells:
            if multi_data is not None:
                well.multicomponent_data = multi_data[well.identifier]
            if melt_data is not None:
                well.melt_curve_raw_data = melt_data[well.identifier]
            for well_item in well.items:
                well_item.amplification_data = amp_data[well_item.identifier][
                    well_item.target_dna_description
                ]
                well_item.result = results_data[well_item.identifier][
                    well_item.target_dna_description.replace(" ", "")
                ]

        return Data(
            header,
            wells,
        )

# header
# sample setup
# raw data
# amplification data
# multicomponent data
# results
# melt curve raw data

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from io import StringIO
import re

import numpy as np
import pandas as pd

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.allotrope.pandas_util import read_csv
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    Referenceable,
)
from allotropy.parsers.utils.pandas import df_to_series_data, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_empty_df,
    assert_not_none,
    try_int,
)


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
        series = pd.Series(raw_data["values"].values, index=raw_data["index"])
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
    reporter_dye_setting: str | None
    position: str | None
    well_location_identifier: str | None
    quencher_dye_setting: str | None
    sample_role_type: str | None
    _amplification_data: AmplificationData | None = None
    _result: Result | None = None

    @property
    def amplification_data(self) -> AmplificationData:
        return assert_not_none(
            self._amplification_data,
            msg=f"Unable to find amplification data for target '{self.target_dna_description}' in well {self.identifier} .",
        )

    @amplification_data.setter
    def amplification_data(self, amplification_data: AmplificationData) -> None:
        self._amplification_data = amplification_data

    @property
    def result(self) -> Result:
        return assert_not_none(
            self._result,
            msg=f"Unable to find result data for well {self.identifier}.",
        )

    @result.setter
    def result(self, result: Result) -> None:
        self._result = result

    @staticmethod
    def create_genotyping(data: SeriesData) -> tuple[WellItem, WellItem]:
        identifier = data[int, "Well"]
        snp_name = data[
            str, "SNP Assay Name", f"Unable to find snp name for well {identifier}"
        ]
        sample_identifier = data.get(str, "Sample Name", NOT_APPLICABLE)
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
                sample_identifier=sample_identifier,
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
                sample_identifier=sample_identifier,
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
    items: dict[str, WellItem]
    _multicomponent_data: MulticomponentData | None = None
    _melt_curve_raw_data: MeltCurveRawData | None = None

    def get_well_item(self, target: str) -> WellItem:
        well_item = self.items.get(target)
        return assert_not_none(
            well_item,
            msg=f"Unable to find target DNA '{target}' for well {self.identifier}.",
        )

    @property
    def multicomponent_data(self) -> MulticomponentData | None:
        return self._multicomponent_data

    @multicomponent_data.setter
    def multicomponent_data(self, multicomponent_data: MulticomponentData) -> None:
        self._multicomponent_data = multicomponent_data

    @property
    def melt_curve_raw_data(self) -> MeltCurveRawData | None:
        return self._melt_curve_raw_data

    @melt_curve_raw_data.setter
    def melt_curve_raw_data(self, melt_curve_raw_data: MeltCurveRawData) -> None:
        self._melt_curve_raw_data = melt_curve_raw_data

    @staticmethod
    def create_genotyping(identifier: int, well_data: SeriesData) -> Well:
        return Well(
            identifier=identifier,
            items={
                well_item.target_dna_description: well_item
                for well_item in WellItem.create_genotyping(well_data)
            },
        )

    @staticmethod
    def create_generic(identifier: int, well_data: pd.DataFrame) -> Well:
        return Well(
            identifier=identifier,
            items={
                item_data["Target Name"]: WellItem.create_generic(SeriesData(item_data))
                for _, item_data in well_data.iterrows()
            },
        )


@dataclass(frozen=True)
class WellList:
    wells: list[Well]

    def iter_well_items(self) -> Iterator[WellItem]:
        for well in self.wells:
            yield from well.items.values()

    def __iter__(self) -> Iterator[Well]:
        return iter(self.wells)

    @staticmethod
    def create(reader: LinesReader, experiment_type: ExperimentType) -> WellList:
        assert_not_none(
            reader.drop_until(r"^\[Sample Setup\]"),
            msg="Unable to find 'Sample Setup' section in file.",
        )

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        data = read_csv(csv_stream, sep="\t").replace(np.nan, None)

        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return WellList(
                [
                    Well.create_genotyping(
                        try_int(str(identifier), "genotyping well identifier"),
                        SeriesData(well_data),
                    )
                    for identifier, well_data in data.iterrows()
                ]
            )
        return WellList(
            [
                Well.create_generic(
                    try_int(str(identifier), "well identifier"),
                    well_data,
                )
                for identifier, well_data in data[
                    data["Target Name"].notnull()
                ].groupby("Well")
            ]
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
    def get_data(reader: LinesReader) -> pd.DataFrame:
        assert_not_none(
            reader.drop_until(r"^\[Amplification Data\]"),
            msg="Unable to find 'Amplification Data' section in file.",
        )

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return read_csv(csv_stream, sep="\t", thousands=r",")

    @staticmethod
    def create(
        amplification_data: pd.DataFrame, well_item: WellItem
    ) -> AmplificationData:
        well_data = assert_not_empty_df(
            amplification_data[amplification_data["Well"] == well_item.identifier],
            msg=f"Unable to find amplification data for well {well_item.identifier}.",
        )

        target_data = assert_not_empty_df(
            well_data[well_data["Target Name"] == well_item.target_dna_description],
            msg=f"Unable to find amplification data for target '{well_item.target_dna_description}' in well {well_item.identifier} .",
        )

        return AmplificationData(
            total_cycle_number_setting=float(target_data["Cycle"].max()),
            cycle=target_data["Cycle"].tolist(),
            rn=target_data["Rn"].tolist(),
            delta_rn=target_data["Delta Rn"].tolist(),
        )


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
    def get_data(reader: LinesReader) -> pd.DataFrame | None:
        if not reader.match(r"^\[Multicomponent Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return read_csv(csv_stream, sep="\t", thousands=r",")

    @staticmethod
    def create(data: pd.DataFrame, well: Well) -> MulticomponentData:
        well_data = assert_not_empty_df(
            data[data["Well"] == well.identifier],
            msg=f"Unable to find multi component data for well {well.identifier}.",
        )

        return MulticomponentData(
            cycle=well_data["Cycle"].tolist(),
            columns={
                name: well_data[name].tolist()  # type: ignore[misc]
                for name in well_data
                if name not in ["Well", "Cycle", "Well Position"]
            },
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
    def get_data(reader: LinesReader) -> tuple[pd.DataFrame, SeriesData]:
        assert_not_none(
            reader.drop_until(r"^\[Results\]"),
            msg="Unable to find 'Results' section in file.",
        )

        reader.pop()  # remove title
        data_lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(data_lines))
        data = read_csv(csv_stream, sep="\t", thousands=r",").replace(np.nan, None)

        reader.drop_empty()

        if reader.match(r"\[.+\]"):
            return data, SeriesData(pd.Series())

        metadata_lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(metadata_lines))
        raw_data = read_csv(csv_stream, header=None, sep="=", names=["index", "values"])
        metadata = pd.Series(raw_data["values"].values, index=raw_data["index"])
        metadata.index = metadata.index.str.strip()

        reader.drop_empty()

        return data, SeriesData(metadata.str.strip())

    @staticmethod
    def create_genotyping(data_frame: pd.DataFrame, well_item: WellItem) -> Result:
        well_data = assert_not_empty_df(
            data_frame[data_frame["Well"] == well_item.identifier],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        snp_assay_name, _ = well_item.target_dna_description.split("-")
        data = df_to_series_data(
            assert_not_empty_df(
                well_data[well_data["SNP Assay Name"] == snp_assay_name],
                msg=f"Unable to find result data for well {well_item.identifier}.",
            ),
            msg=f"Expected exactly 1 row of results to be associated with target '{well_item.target_dna_description}' in well {well_item.identifier}.",
        )

        _, raw_allele = well_item.target_dna_description.split("-")
        allele = raw_allele.replace(" ", "")

        return Result(
            cycle_threshold_value_setting=data[
                float,
                f"{allele} Ct Threshold",
                "Unable to find cycle threshold value setting for well {well_item.identifier}",
            ],
            # TODO(nstender): really seems like this should be NaN if invalid value. Keeping to preserve tests.
            cycle_threshold_result=data.get(float, f"{allele} Ct"),
            automatic_cycle_threshold_enabled_setting=data.get(
                bool, f"{allele} Automatic Ct Threshold"
            ),
            automatic_baseline_determination_enabled_setting=data.get(
                bool, f"{allele} Automatic Baseline"
            ),
            normalized_reporter_result=data.get(float, "Rn"),
            baseline_corrected_reporter_result=data.get(float, f"{allele} Delta Rn"),
            genotyping_determination_result=data.get(str, "Call"),
            genotyping_determination_method_setting=data.get(float, "Threshold Value"),
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

    @staticmethod
    def create_generic(data_frame: pd.DataFrame, well_item: WellItem) -> Result:
        well_data = assert_not_empty_df(
            data_frame[data_frame["Well"] == well_item.identifier],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        data = df_to_series_data(
            assert_not_empty_df(
                well_data[well_data["Target Name"] == well_item.target_dna_description],
                msg=f"Unable to find result data for well {well_item.identifier}.",
            ),
            msg=f"Expected exactly 1 row of results to be associated with target '{well_item.target_dna_description}' in well {well_item.identifier}.",
        )

        return Result(
            cycle_threshold_value_setting=assert_not_none(
                data.get(float, "Ct Threshold"),
                msg=f"Unable to find cycle threshold value setting for well {well_item.identifier}",
            ),
            # TODO(nstender): really seems like this should be NaN if invalid value. Keeping to preserve tests.
            cycle_threshold_result=data.get(float, "CT"),
            automatic_cycle_threshold_enabled_setting=data.get(
                bool, "Automatic Ct Threshold"
            ),
            automatic_baseline_determination_enabled_setting=data.get(
                bool, "Automatic Baseline"
            ),
            normalized_reporter_result=data.get(float, "Rn"),
            baseline_corrected_reporter_result=data.get(float, "Delta Rn"),
            genotyping_determination_result=data.get(str, "Call"),
            genotyping_determination_method_setting=data.get(float, "Threshold Value"),
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

    @staticmethod
    def create(
        data: pd.DataFrame, well_item: WellItem, experiment_type: ExperimentType
    ) -> Result:
        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return Result.create_genotyping(data, well_item)
        return Result.create_generic(data, well_item)


@dataclass(frozen=True)
class MeltCurveRawData:
    reading: list[float]
    fluorescence: list[float | None]
    derivative: list[float | None]

    @staticmethod
    def create(data: pd.DataFrame, well: Well) -> MeltCurveRawData:
        well_data = assert_not_empty_df(
            data[data["Well"] == well.identifier],
            msg=f"Unable to find melt curve raw data for well {well.identifier}.",
        )
        return MeltCurveRawData(
            reading=well_data["Reading"].tolist(),
            fluorescence=well_data["Fluorescence"].tolist(),
            derivative=well_data["Derivative"].tolist(),
        )

    @staticmethod
    def get_data(reader: LinesReader) -> pd.DataFrame | None:
        if not reader.match(r"^\[Melt Curve Raw Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(lines))
        return read_csv(csv_stream, sep="\t", thousands=r",")


@dataclass(frozen=True)
class Data:
    header: Header
    wells: WellList
    raw_data: RawData | None
    endogenous_control: str
    reference_sample: str
    calculated_documents: list[CalculatedDocument]

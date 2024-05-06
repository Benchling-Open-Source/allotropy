from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import Optional

import pandas as pd

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    Referenceable,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_df_column,
    assert_not_empty_df,
    assert_not_none,
    df_to_series,
    try_bool_from_series_or_none,
    try_float,
    try_float_from_series,
    try_float_from_series_or_none,
    try_float_or_none,
    try_int,
    try_int_from_series,
    try_str_from_series,
    try_str_from_series_or_none,
)

SAMPLE_ROLE_TYPES_MAP = {
    "NTC": "negative control sample role",
    "STANDARD": "standard sample role",
    "UNKNOWN": "unknown sample role",
    "POSITIVE CONTROL": "positive control sample role",
    "IPC": "reference DNA control sample role",
    "BLOCKED_IPC": "DNA amplification control sample role",
    "POSITIVE_1/1": "homozygous control sample role",
    "POSITIVE_2/2": "homozygous control sample role",
    "POSITIVE_1/2": "heterozygous control sample role",
}


@dataclass(frozen=True)
class Header:
    measurement_time: str
    plate_well_count: int
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    pcr_detection_chemistry: str
    passive_reference_dye_setting: Optional[str]
    barcode: Optional[str]
    analyst: Optional[str]
    experimental_data_identifier: Optional[str]
    pcr_stage_number: int
    software_name: Optional[str]
    software_version: Optional[str]
    block_serial_number: Optional[str]
    heated_cover_serial_number: Optional[str]

    @staticmethod
    def create(header: pd.Series[str]) -> Header:
        software_info = assert_not_none(
            re.match(
                "(.*) v(.+)",
                try_str_from_series(header, "Software Name and Version"),
            )
        )

        return Header(
            measurement_time=try_str_from_series(header, "Run End Data/Time"),
            plate_well_count=assert_not_none(
                try_int(
                    assert_not_none(
                        re.match(
                            "(96)|(384)",
                            try_str_from_series(header, "Block Type"),
                        ),
                        msg="Unable to find plate well count",
                    ).group(),
                    "plate well count",
                ),
                msg="Unable to interpret plate well count",
            ),
            device_identifier=(
                try_str_from_series_or_none(header, "Instrument Name") or "NA"
            ),
            model_number=try_str_from_series_or_none(header, "Instrument Type") or "NA",
            device_serial_number=(
                try_str_from_series_or_none(header, "Instrument Serial Number") or "NA"
            ),
            measurement_method_identifier=try_str_from_series(
                header, "Quantification Cycle Method"
            ),
            pcr_detection_chemistry=(
                try_str_from_series_or_none(header, "Chemistry") or "NA"
            ),
            passive_reference_dye_setting=try_str_from_series_or_none(
                header, "Passive Reference"
            ),
            barcode=try_str_from_series_or_none(header, "Barcode"),
            analyst=try_str_from_series_or_none(header, "Operator"),
            experimental_data_identifier=try_str_from_series_or_none(
                header, "Experiment Name"
            ),
            block_serial_number=try_str_from_series_or_none(
                header, "Block Serial Number"
            ),
            heated_cover_serial_number=try_str_from_series_or_none(
                header, "Heated Cover Serial Number"
            ),
            pcr_stage_number=assert_not_none(
                try_int(
                    assert_not_none(
                        re.match(
                            r"Stage (\d+)",
                            try_str_from_series(header, r"PCR Stage/Step Number"),
                        ),
                        msg="Unable to find PCR Stage Number",
                    ).group(1),
                    "PCR Stage Number",
                ),
                msg=r"Unable to interpret PCR Stage/Step Number",
            ),
            software_name=software_info.group(1),
            software_version=software_info.group(2),
        )


@dataclass
class WellItem(Referenceable):
    identifier: int
    target_dna_description: str
    sample_identifier: str
    reporter_dye_setting: Optional[str]
    well_location_identifier: Optional[str]
    quencher_dye_setting: Optional[str]
    sample_role_type: Optional[str]
    amplification_data: AmplificationData
    result: Result
    melt_curve_data: Optional[MeltCurveData] = None

    @staticmethod
    def create(
        contents: DesignQuantstudioContents,
        data: pd.Series[str],
        experiment_type: ExperimentType,
    ) -> WellItem:
        identifier = try_int_from_series(data, "Well")

        target_dna_description = try_str_from_series(
            data,
            "Target",
            msg=f"Unable to find target dna description for well {identifier}",
        )

        well_position = try_str_from_series(
            data,
            "Well Position",
            msg=f"Unable to find well position for Well '{identifier}'.",
        )

        sample_identifier = try_str_from_series_or_none(data, "Sample") or well_position

        raw_sample_role_type = try_str_from_series_or_none(data, "Task")
        sample_role_type = (
            None
            if raw_sample_role_type is None
            else SAMPLE_ROLE_TYPES_MAP.get(raw_sample_role_type)
        )

        amp_data = contents.get_non_empty_sheet("Amplification Data")
        melt_curve_data = contents.get_non_empty_sheet_or_none("Melt Curve Raw")

        return WellItem(
            uuid=random_uuid_str(),
            identifier=identifier,
            target_dna_description=target_dna_description,
            sample_identifier=sample_identifier,
            reporter_dye_setting=try_str_from_series_or_none(data, "Reporter"),
            well_location_identifier=well_position,
            quencher_dye_setting=try_str_from_series_or_none(data, "Quencher"),
            sample_role_type=sample_role_type,
            amplification_data=AmplificationData.create(
                amp_data, identifier, target_dna_description
            ),
            melt_curve_data=(
                None
                if melt_curve_data is None
                else MeltCurveData.create(
                    melt_curve_data, identifier, target_dna_description
                )
            ),
            result=Result.create(
                contents, identifier, target_dna_description, experiment_type
            ),
        )


@dataclass
class Well:
    identifier: int
    items: dict[str, WellItem]
    multicomponent_data: Optional[MulticomponentData] = None

    def get_well_item(self, target: str) -> WellItem:
        well_item = self.items.get(target)
        return assert_not_none(
            well_item,
            msg=f"Unable to find target DNA '{target}' for well {self.identifier}.",
        )

    @staticmethod
    def create(
        contents: DesignQuantstudioContents,
        header: Header,
        well_data: pd.DataFrame,
        identifier: int,
        experiment_type: ExperimentType,
    ) -> Well:
        well_items = {
            try_str_from_series(item_data, "Target"): WellItem.create(
                contents, item_data, experiment_type
            )
            for _, item_data in well_data.iterrows()
        }

        multi_data = contents.get_non_empty_sheet_or_none("Multicomponent")
        return Well(
            identifier=identifier,
            items=well_items,
            multicomponent_data=(
                None
                if multi_data is None
                else MulticomponentData.create(header, multi_data, identifier)
            ),
        )


@dataclass(frozen=True)
class WellList:
    wells: list[Well]

    def get_well_items(self) -> list[WellItem]:
        wells: list[WellItem] = []
        for well in self.wells:
            wells += well.items.values()
        return wells

    def __iter__(self) -> Iterator[Well]:
        return iter(self.wells)

    @staticmethod
    def create(
        contents: DesignQuantstudioContents,
        header: Header,
        experiment_type: ExperimentType,
    ) -> WellList:
        results_data = contents.get_non_empty_sheet("Results")
        assert_df_column(results_data, "Well")
        return WellList(
            wells=[
                Well.create(
                    contents,
                    header,
                    well_data,
                    try_int(str(identifier), "well identifier"),
                    experiment_type,
                )
                for identifier, well_data in results_data.groupby("Well")
            ]
        )


@dataclass(frozen=True)
class AmplificationData:
    total_cycle_number_setting: float
    cycle: list[float]
    rn: list[Optional[float]]
    delta_rn: list[Optional[float]]

    @staticmethod
    def create(
        amplification_data: pd.DataFrame,
        well_item_id: int,
        target_dna_description: str,
    ) -> AmplificationData:
        well_data = assert_not_empty_df(
            amplification_data[
                assert_df_column(amplification_data, "Well") == well_item_id
            ],
            msg=f"Unable to find amplification data for well {well_item_id}.",
        )

        target_data = assert_not_empty_df(
            well_data[assert_df_column(well_data, "Target") == target_dna_description],
            msg=f"Unable to find amplification data for target '{target_dna_description}' in well {well_item_id} .",
        )

        cycle_number = assert_df_column(target_data, "Cycle Number")
        return AmplificationData(
            total_cycle_number_setting=try_float(cycle_number.max(), "Cycle Number"),
            cycle=cycle_number.tolist(),
            rn=assert_df_column(target_data, "Rn").tolist(),
            delta_rn=assert_df_column(target_data, "dRn").tolist(),
        )


@dataclass(frozen=True)
class MulticomponentData:
    cycle: list[float]
    columns: dict[str, list[Optional[float]]]

    def get_column(self, name: str) -> list[Optional[float]]:
        return assert_not_none(
            self.columns.get(name),
            msg=f"Unable to obtain '{name}' from multicomponent data.",
        )

    @staticmethod
    def create(header: Header, data: pd.DataFrame, well_id: int) -> MulticomponentData:
        well_data = assert_not_empty_df(
            data[assert_df_column(data, "Well") == well_id],
            msg=f"Unable to find multi component data for well {well_id}.",
        )

        stage_data = assert_not_empty_df(
            well_data[
                assert_df_column(well_data, "Stage Number") == header.pcr_stage_number
            ],
            msg=f"Unable to find multi component data for stage {header.pcr_stage_number}.",
        )

        return MulticomponentData(
            cycle=assert_df_column(stage_data, "Cycle Number").tolist(),
            columns={
                str(name): stage_data[name].tolist()
                for name in stage_data
                if name
                not in [
                    "Well",
                    "Cycle Number",
                    "Well Position",
                    "Stage Number",
                    "Step Number",
                ]
            },
        )


@dataclass(frozen=True)
class MeltCurveData:
    target: str
    temperature: list[float]
    fluorescence: list[Optional[float]]
    derivative: list[Optional[float]]

    @staticmethod
    def create(
        data: pd.DataFrame, well_id: int, target_dna_description: str
    ) -> MeltCurveData:
        well_data = assert_not_empty_df(
            data[assert_df_column(data, "Well") == well_id],
            msg=f"Unable to find melt curve data for well {well_id}.",
        )

        target_data = assert_not_empty_df(
            well_data[assert_df_column(well_data, "Target") == target_dna_description],
            msg=f"Unable to find melt curve data for target '{target_dna_description}' in well {well_id} .",
        )

        return MeltCurveData(
            target=target_dna_description,
            temperature=assert_df_column(target_data, "Temperature").tolist(),
            fluorescence=assert_df_column(target_data, "Fluorescence").tolist(),
            derivative=assert_df_column(target_data, "Derivative").tolist(),
        )


@dataclass(frozen=True)
class Result:
    cycle_threshold_value_setting: float
    cycle_threshold_result: Optional[float]
    automatic_cycle_threshold_enabled_setting: Optional[bool]
    automatic_baseline_determination_enabled_setting: Optional[bool]
    normalized_reporter_result: Optional[float]
    baseline_corrected_reporter_result: Optional[float]
    baseline_determination_start_cycle_setting: Optional[float]
    baseline_determination_end_cycle_setting: Optional[float]
    genotyping_determination_result: Optional[str]
    genotyping_determination_method_setting: Optional[float]
    quantity: Optional[float]
    quantity_mean: Optional[float]
    quantity_sd: Optional[float]
    ct_mean: Optional[float]
    eq_ct_mean: Optional[float]
    adj_eq_ct_mean: Optional[float]
    ct_sd: Optional[float]
    ct_se: Optional[float]
    delta_ct_mean: Optional[float]
    delta_ct_se: Optional[float]
    delta_ct_sd: Optional[float]
    delta_delta_ct: Optional[float]
    rq: Optional[float]
    rq_min: Optional[float]
    rq_max: Optional[float]
    rn_mean: Optional[float]
    rn_sd: Optional[float]
    y_intercept: Optional[float]
    r_squared: Optional[float]
    slope: Optional[float]
    efficiency: Optional[float]

    @staticmethod
    def get_reference_sample(contents: DesignQuantstudioContents) -> str:
        data = contents.get_non_empty_sheet("RQ Replicate Group Result")
        return try_str_from_series(
            df_to_series(
                data[assert_df_column(data, "Rq") == 1],
                msg="Unable to find Rq related to reference sample.",
            ),
            "Sample",
            msg="Unable to infer reference sample.",
        )

    @staticmethod
    def get_reference_target(contents: DesignQuantstudioContents) -> str:
        data = contents.get_non_empty_sheet("RQ Replicate Group Result")
        sub_data = data[assert_df_column(data, "Rq").isnull()]
        target = assert_df_column(sub_data, "Target").unique()
        if target.size != 1:
            error = "Unable to infer reference target."
            raise AllotropeConversionError(error)
        return str(target[0])

    @staticmethod
    def _add_data(
        data: pd.DataFrame, extra_data: pd.DataFrame, columns: list[str]
    ) -> None:

        data[columns] = None
        for _, row in extra_data.iterrows():
            sample_cond = data["Sample"] == row["Sample"]
            target_cond = data["Target"] == row["Target"]
            data.loc[sample_cond & target_cond, columns] = row[columns].to_list()

    @staticmethod
    def create(
        contents: DesignQuantstudioContents,
        well_item_id: int,
        target_dna_description: str,
        experiment_type: ExperimentType,
    ) -> Result:
        data_sheet = (
            "Standard Curve Result"
            if experiment_type == ExperimentType.standard_curve_qPCR_experiment
            else "Results"
        )

        data = contents.get_non_empty_sheet(data_sheet)

        if experiment_type == ExperimentType.relative_standard_curve_qPCR_experiment:
            Result._add_data(
                data,
                extra_data=contents.get_non_empty_sheet("Replicate Group Result"),
                columns=[
                    "Cq SE",
                ],
            )

            Result._add_data(
                data,
                extra_data=contents.get_non_empty_sheet("RQ Replicate Group Result"),
                columns=[
                    "EqCq Mean",
                    "Adjusted EqCq Mean",
                    "Delta EqCq Mean",
                    "Delta EqCq SD",
                    "Delta EqCq SE",
                    "Delta Delta EqCq",
                    "Rq",
                    "Rq Min",
                    "Rq Max",
                ],
            )

        well_data = assert_not_empty_df(
            data[assert_df_column(data, "Well") == well_item_id],
            msg=f"Unable to find result data for well {well_item_id}.",
        )

        target_data = df_to_series(
            assert_not_empty_df(
                well_data[
                    assert_df_column(well_data, "Target") == target_dna_description
                ],
                msg=f"Unable to find result data for well {well_item_id}.",
            ),
            msg=f"Expected exactly 1 row of results to be associated with target '{target_dna_description}' in well {well_item_id}.",
        )

        genotyping_determination_result = (
            try_str_from_series_or_none(target_data, "Call")
            if experiment_type == ExperimentType.presence_absence_qPCR_experiment
            else None
        )

        genotyping_determination_method_setting = (
            try_float_from_series_or_none(target_data, "Threshold")
            if experiment_type
            in (
                ExperimentType.presence_absence_qPCR_experiment,
                ExperimentType.genotyping_qPCR_experiment,
            )
            else None
        )

        return Result(
            cycle_threshold_value_setting=try_float_from_series(
                target_data,
                "Threshold",
                msg=f"Unable to find cycle threshold value setting for well {well_item_id}",
            ),
            cycle_threshold_result=try_float_or_none(str(target_data.get("Cq"))),
            automatic_cycle_threshold_enabled_setting=try_bool_from_series_or_none(
                target_data, "Auto Threshold"
            ),
            automatic_baseline_determination_enabled_setting=try_bool_from_series_or_none(
                target_data, "Auto Baseline"
            ),
            normalized_reporter_result=try_float_from_series_or_none(target_data, "Rn"),
            baseline_corrected_reporter_result=try_float_from_series_or_none(
                target_data, "Delta Rn"
            ),
            baseline_determination_start_cycle_setting=try_float_from_series_or_none(
                target_data, "Baseline Start"
            ),
            baseline_determination_end_cycle_setting=try_float_from_series_or_none(
                target_data, "Baseline End"
            ),
            genotyping_determination_result=genotyping_determination_result,
            genotyping_determination_method_setting=genotyping_determination_method_setting,
            quantity=try_float_from_series_or_none(target_data, "Quantity"),
            quantity_mean=try_float_from_series_or_none(target_data, "Quantity Mean"),
            quantity_sd=try_float_from_series_or_none(target_data, "Quantity SD"),
            ct_mean=try_float_from_series_or_none(target_data, "Cq Mean"),
            eq_ct_mean=try_float_from_series_or_none(target_data, "EqCq Mean"),
            adj_eq_ct_mean=try_float_from_series_or_none(
                target_data, "Adjusted EqCq Mean"
            ),
            ct_sd=try_float_from_series_or_none(target_data, "Cq SD"),
            ct_se=try_float_from_series_or_none(target_data, "Cq SE"),
            delta_ct_mean=try_float_from_series_or_none(target_data, "Delta EqCq Mean"),
            delta_ct_se=try_float_from_series_or_none(target_data, "Delta EqCq SE"),
            delta_ct_sd=try_float_from_series_or_none(target_data, "Delta EqCq SD"),
            delta_delta_ct=try_float_from_series_or_none(
                target_data, "Delta Delta EqCq"
            ),
            rq=try_float_from_series_or_none(target_data, "Rq"),
            rq_min=try_float_from_series_or_none(target_data, "Rq Min"),
            rq_max=try_float_from_series_or_none(target_data, "Rq Max"),
            rn_mean=try_float_from_series_or_none(target_data, "Rn Mean"),
            rn_sd=try_float_from_series_or_none(target_data, "Rn SD"),
            y_intercept=try_float_from_series_or_none(target_data, "Y-Intercept"),
            r_squared=try_float_from_series_or_none(target_data, "R2"),
            slope=try_float_from_series_or_none(target_data, "Slope"),
            efficiency=try_float_from_series_or_none(target_data, "Efficiency"),
        )


@dataclass(frozen=True)
class Data:
    header: Header
    wells: WellList
    experiment_type: ExperimentType
    calculated_documents: list[CalculatedDocument]
    reference_target: Optional[str]
    reference_sample: Optional[str]

    @staticmethod
    def get_experiment_type(contents: DesignQuantstudioContents) -> ExperimentType:
        if contents.get_non_empty_sheet_or_none("Standard Curve Result") is not None:
            return ExperimentType.standard_curve_qPCR_experiment

        if (
            contents.get_non_empty_sheet_or_none("RQ Replicate Group Result")
            is not None
        ):
            return ExperimentType.relative_standard_curve_qPCR_experiment

        if contents.get_non_empty_sheet_or_none("Genotyping Result") is not None:
            return ExperimentType.genotyping_qPCR_experiment

        if all(
            contents.get_non_empty_sheet_or_none(sheet) is not None
            for sheet in ["Melt Curve Raw", "Melt Curve Result"]
        ):
            return ExperimentType.melt_curve_qPCR_experiment

        if all(
            contents.get_non_empty_sheet_or_none(sheet) is not None
            for sheet in ["Sample Call", "Well Call", "Target Call", "Control Status"]
        ):
            return ExperimentType.presence_absence_qPCR_experiment

        error = "Unable to infer expermient type"
        raise AllotropeConversionError(error)

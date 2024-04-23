from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional

import pandas as pd

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
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


class ExperimentType(Enum):
    STANDARD_CURVE = "Standard Curve Experiment"
    RELATIVE_QUANTIFICATION = (
        "Relative Quantification/Relative Standard Curve Experiment"
    )
    MELT_CURVE = "Melt Curve Experiment"
    GENOTYPING = "Genotyping Experiment"
    PRESENCE_ABSENCE = "Presence/Absence Experiment"
    UNKNOWN = "Unknown experiment"


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
class WellItem:
    uuid: str
    identifier: int
    target_dna_description: str
    sample_identifier: str
    reporter_dye_setting: Optional[str]
    well_location_identifier: Optional[str]
    quencher_dye_setting: Optional[str]
    sample_role_type: Optional[str]
    _amplification_data: Optional[AmplificationData] = None
    _melt_curve_data: Optional[MeltCurveData] = None
    _result: Optional[Result] = None

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
    def melt_curve_data(self) -> Optional[MeltCurveData]:
        return self._melt_curve_data

    @melt_curve_data.setter
    def melt_curve_data(self, melt_curve_data: MeltCurveData) -> None:
        self._melt_curve_data = melt_curve_data

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
    def create(data: pd.Series[str]) -> WellItem:
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

        return WellItem(
            uuid=random_uuid_str(),
            identifier=identifier,
            target_dna_description=target_dna_description,
            sample_identifier=sample_identifier,
            reporter_dye_setting=try_str_from_series_or_none(data, "Reporter"),
            well_location_identifier=well_position,
            quencher_dye_setting=try_str_from_series_or_none(data, "Quencher"),
            sample_role_type=sample_role_type,
        )


@dataclass
class Well:
    identifier: int
    items: dict[str, WellItem]
    _multicomponent_data: Optional[MulticomponentData] = None

    def get_well_item(self, target: str) -> WellItem:
        well_item = self.items.get(target)
        return assert_not_none(
            well_item,
            msg=f"Unable to find target DNA '{target}' for well {self.identifier}.",
        )

    @property
    def multicomponent_data(self) -> Optional[MulticomponentData]:
        return self._multicomponent_data

    @multicomponent_data.setter
    def multicomponent_data(self, multicomponent_data: MulticomponentData) -> None:
        self._multicomponent_data = multicomponent_data

    @staticmethod
    def create(identifier: int, well_data: pd.DataFrame) -> Well:
        return Well(
            identifier=identifier,
            items={
                try_str_from_series(item_data, "Target"): WellItem.create(item_data)
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
    def create(results_data: pd.DataFrame) -> WellList:
        assert_df_column(results_data, "Well")
        return WellList(
            [
                Well.create(
                    try_int(str(identifier), "well identifier"),
                    well_data,
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
        amplification_data: pd.DataFrame, well_item: WellItem
    ) -> AmplificationData:
        well_data = assert_not_empty_df(
            amplification_data[
                assert_df_column(amplification_data, "Well") == well_item.identifier
            ],
            msg=f"Unable to find amplification data for well {well_item.identifier}.",
        )

        target_data = assert_not_empty_df(
            well_data[
                assert_df_column(well_data, "Target")
                == well_item.target_dna_description
            ],
            msg=f"Unable to find amplification data for target '{well_item.target_dna_description}' in well {well_item.identifier} .",
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
    def create(data: pd.DataFrame, well: Well, header: Header) -> MulticomponentData:
        well_data = assert_not_empty_df(
            data[assert_df_column(data, "Well") == well.identifier],
            msg=f"Unable to find multi component data for well {well.identifier}.",
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
    def create(data: pd.DataFrame, well: Well, well_item: WellItem) -> MeltCurveData:
        well_data = assert_not_empty_df(
            data[assert_df_column(data, "Well") == well.identifier],
            msg=f"Unable to find melt curve data for well {well.identifier}.",
        )

        target_data = assert_not_empty_df(
            well_data[
                assert_df_column(well_data, "Target")
                == well_item.target_dna_description
            ],
            msg=f"Unable to find melt curve data for target '{well_item.target_dna_description}' in well {well_item.identifier} .",
        )

        return MeltCurveData(
            target=well_item.target_dna_description,
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
    ct_sd: Optional[float]
    delta_ct_mean: Optional[float]
    delta_ct_se: Optional[float]
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
    def create(
        data: pd.DataFrame, well_item: WellItem, experiment_type: ExperimentType
    ) -> Result:
        well_data = assert_not_empty_df(
            data[assert_df_column(data, "Well") == well_item.identifier],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        target_data = df_to_series(
            assert_not_empty_df(
                well_data[
                    assert_df_column(well_data, "Target")
                    == well_item.target_dna_description
                ],
                msg=f"Unable to find result data for well {well_item.identifier}.",
            ),
            msg=f"Expected exactly 1 row of results to be associated with target '{well_item.target_dna_description}' in well {well_item.identifier}.",
        )

        genotyping_determination_result = (
            try_str_from_series_or_none(target_data, "Call")
            if experiment_type == ExperimentType.PRESENCE_ABSENCE
            else None
        )

        genotyping_determination_method_setting = (
            try_float_from_series_or_none(target_data, "Threshold")
            if experiment_type
            in (ExperimentType.PRESENCE_ABSENCE, ExperimentType.GENOTYPING)
            else None
        )

        return Result(
            cycle_threshold_value_setting=try_float_from_series(
                target_data,
                "Threshold",
                msg=f"Unable to find cycle threshold value setting for well {well_item.identifier}",
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
            ct_sd=try_float_from_series_or_none(target_data, "Cq SD"),
            delta_ct_mean=try_float_from_series_or_none(target_data, "Delta Ct Mean"),
            delta_ct_se=try_float_from_series_or_none(target_data, "Delta Ct SE"),
            delta_delta_ct=try_float_from_series_or_none(target_data, "Delta Delta Ct"),
            rq=try_float_from_series_or_none(target_data, "RQ"),
            rq_min=try_float_from_series_or_none(target_data, "RQ Min"),
            rq_max=try_float_from_series_or_none(target_data, "RQ Max"),
            rn_mean=try_float_from_series_or_none(target_data, "Rn Mean"),
            rn_sd=try_float_from_series_or_none(target_data, "Rn SD"),
            y_intercept=try_float_from_series_or_none(target_data, "Y-Intercept"),
            r_squared=try_float_from_series_or_none(target_data, "R(superscript 2)"),
            slope=try_float_from_series_or_none(target_data, "Slope"),
            efficiency=try_float_from_series_or_none(target_data, "Efficiency"),
        )


@dataclass(frozen=True)
class Data:
    header: Header
    wells: WellList
    experiment_type: ExperimentType

    @staticmethod
    def get_experiment_type(contents: DesignQuantstudioContents) -> ExperimentType:
        if contents.get_non_empty_sheet_or_none("Standard Curve Result") is not None:
            return ExperimentType.STANDARD_CURVE

        if (
            contents.get_non_empty_sheet_or_none("RQ Replicate Group Result")
            is not None
        ):
            return ExperimentType.RELATIVE_QUANTIFICATION

        if contents.get_non_empty_sheet_or_none("Genotyping Result") is not None:
            return ExperimentType.GENOTYPING

        if all(
            contents.get_non_empty_sheet_or_none(sheet) is not None
            for sheet in ["Melt Curve Raw", "Melt Curve Result"]
        ):
            return ExperimentType.MELT_CURVE

        if all(
            contents.get_non_empty_sheet_or_none(sheet) is not None
            for sheet in ["Sample Call", "Well Call", "Target Call", "Control Status"]
        ):
            return ExperimentType.PRESENCE_ABSENCE

        return ExperimentType.UNKNOWN

    @staticmethod
    def create(contents: DesignQuantstudioContents) -> Data:
        amp_data = contents.get_non_empty_sheet("Amplification Data")
        multi_data = contents.get_non_empty_sheet_or_none("Multicomponent")
        results_data = contents.get_non_empty_sheet("Results")
        melt_curve_data = contents.get_non_empty_sheet_or_none("Melt Curve Raw")

        experiment_type = Data.get_experiment_type(contents)

        header = Header.create(contents.header)
        wells = WellList.create(results_data)

        for well in wells:
            if multi_data is not None:
                well.multicomponent_data = MulticomponentData.create(
                    multi_data, well, header
                )

            for well_item in well.items.values():
                if melt_curve_data is not None:
                    well_item.melt_curve_data = MeltCurveData.create(
                        melt_curve_data, well, well_item
                    )

                well_item.amplification_data = AmplificationData.create(
                    amp_data,
                    well_item,
                )

                well_item.result = Result.create(
                    results_data,
                    well_item,
                    experiment_type,
                )

        return Data(
            header,
            wells,
            experiment_type,
        )

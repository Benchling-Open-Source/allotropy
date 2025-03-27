from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import PureWindowsPath
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import SampleRoleType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    MulticomponentData,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.constants import (
    ExperimentType,
)
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    Referenceable,
)
from allotropy.parsers.utils.pandas import (
    assert_df_column,
    assert_not_empty_df,
    SeriesData,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_int,
)

SAMPLE_ROLE_TYPES_MAP = {
    "NTC": SampleRoleType.control_sample_role,
    "STANDARD": SampleRoleType.standard_sample_role,
    "UNKNOWN": SampleRoleType.unknown_sample_role,
    "POSITIVE_CONTROL": SampleRoleType.control_sample_role,
    "IPC": SampleRoleType.control_sample_role,
    "BLOCKED_IPC": SampleRoleType.control_sample_role,
    "BLOCKEDIPC": SampleRoleType.control_sample_role,
    "PC_ALLELE_1": SampleRoleType.control_sample_role,
    "PC_ALLELE_2": SampleRoleType.control_sample_role,
    "PC_ALLELE_BOTH": SampleRoleType.control_sample_role,
    "POSITIVE_11": SampleRoleType.control_sample_role,
    "POSITIVE_22": SampleRoleType.control_sample_role,
    "POSITIVE_12": SampleRoleType.control_sample_role,
    "Accuracy Control": SampleRoleType.control_sample_role,
}


def get_well_volume(block_type: str) -> float:
    # if the block type includes the well volume in mL, convert to microliters
    if well_search := re.search(r"([0-9]+\.[0-9]+)-?mL", block_type):
        return float(well_search.groups()[0]) * 1000
    # The 384-well block and Taqman Array Card have specified well volumes from the
    # manufacturer (Thermo Fisher) which are 40uL and 1.5uL, respectively.
    elif "384-Well Block" in block_type:
        return 40
    elif "Taqman Array Card" in block_type:
        return 1.5
    # Since well volume is required, if it cannot be implied from block type
    # a negative zero will be returned, indicating an error.
    return NEGATIVE_ZERO


@dataclass(frozen=True)
class Header:
    measurement_time: str
    plate_well_count: int
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    well_volume: float
    pcr_detection_chemistry: str | None
    passive_reference_dye_setting: str | None
    barcode: str | None
    analyst: str | None
    experimental_data_identifier: str
    pcr_stage_number: int | None
    software_name: str | None
    software_version: str | None
    block_serial_number: str | None
    heated_cover_serial_number: str | None

    @staticmethod
    def create(header: SeriesData) -> Header:
        software_info = re.match(
            "(.*) v(.+)",
            header.get(str, "Software Name and Version", ""),
        )

        software_name, software_version = (
            (software_info.group(1), software_info.group(2))
            if software_info
            else (None, None)
        )

        stage_number_raw = header.get(str, "PCR Stage/Step Number", "")
        stage_number = re.match(r"Stage (\d+)", stage_number_raw)
        pcr_stage_number = None if stage_number is None else int(stage_number.group(1))
        block_type = header[str, "Block Type"]

        return Header(
            measurement_time=header[
                str,
                ["Run End Date/Time", "Run End Data/Time"],
                "Unable to find measurement time.",
            ],
            plate_well_count=assert_not_none(
                try_int(
                    assert_not_none(
                        re.match("(96)|(384)", block_type),
                        msg="Unable to find plate well count",
                    ).group(),
                    "plate well count",
                ),
                msg="Unable to interpret plate well count",
            ),
            device_identifier=header.get(str, "Instrument Name", NOT_APPLICABLE),
            model_number=header.get(str, "Instrument Type", NOT_APPLICABLE),
            device_serial_number=header.get(
                str, "Instrument Serial Number", NOT_APPLICABLE
            ),
            measurement_method_identifier=header[str, "Quantification Cycle Method"],
            pcr_detection_chemistry=header.get(str, "Chemistry"),
            passive_reference_dye_setting=header.get(str, "Passive Reference"),
            barcode=header.get(str, "Barcode"),
            analyst=header.get(str, "Operator"),
            experimental_data_identifier=PureWindowsPath(header[str, "File Name"]).name,
            block_serial_number=header.get(str, "Block Serial Number"),
            heated_cover_serial_number=header.get(str, "Heated Cover Serial Number"),
            pcr_stage_number=pcr_stage_number,
            software_name=software_name,
            software_version=software_version,
            well_volume=get_well_volume(block_type),
        )


@dataclass
class WellItem(Referenceable):
    identifier: int
    target_dna_description: str
    sample_identifier: str
    location_identifier: str
    reporter_dye_setting: str | None
    well_location_identifier: str | None
    quencher_dye_setting: str | None
    sample_role_type: SampleRoleType | None
    amplification_data: AmplificationData | None
    result: Result
    melt_curve_data: MeltCurveData | None = None
    sample_custom_info: dict[str, Any] | None = None

    @classmethod
    def get_result_class(cls) -> type[Result]:
        return Result

    # Make hashable to allow for use of caching
    def __hash__(self) -> int:
        return hash(self.identifier)

    @classmethod
    def get_amplification_data_sheet(
        cls, reader: DesignQuantstudioReader
    ) -> pd.DataFrame | None:
        return reader.get_non_empty_sheet("Amplification Data")

    @classmethod
    def create(
        cls,
        reader: DesignQuantstudioReader,
        data: SeriesData,
    ) -> WellItem:
        identifier = data[int, "Well"]

        target_dna_description = data[
            str,
            "Target",
            f"Unable to find target dna description for well {identifier}",
        ]
        well_position = data[
            str,
            "Well Position",
            f"Unable to find well position for Well '{identifier}'.",
        ]

        amp_data = cls.get_amplification_data_sheet(reader)
        amplification_data = (
            create_amplification_data(amp_data, identifier, target_dna_description)
            if amp_data is not None
            else None
        )

        melt_data = reader.get_non_empty_sheet_or_none("Melt Curve Raw")
        melt_curve_data = (
            MeltCurveData.create(melt_data, identifier, target_dna_description)
            if melt_data is not None
            else None
        )

        result_class = cls.get_result_class()
        result = result_class.create(data, identifier)

        return WellItem(
            uuid=random_uuid_str(),
            identifier=identifier,
            target_dna_description=target_dna_description,
            sample_identifier=data.get(str, "Sample", well_position),
            reporter_dye_setting=data.get(str, "Reporter"),
            well_location_identifier=well_position,
            location_identifier=str(identifier),
            quencher_dye_setting=data.get(str, "Quencher"),
            sample_role_type=SAMPLE_ROLE_TYPES_MAP.get(
                data.get(str, "Task", "__INVALID_KEY__")
            ),
            amplification_data=amplification_data,
            melt_curve_data=melt_curve_data,
            result=result,
            sample_custom_info=(
                {"quantity": result.quantity}
                if result.cycle_threshold_result is None and result.quantity is not None
                else None
            ),
        )


@dataclass
class Well:
    identifier: int
    items: dict[str, WellItem]
    multicomponent_data: MulticomponentData | None = None

    def get_well_item(self, target: str) -> WellItem:
        return assert_not_none(
            self.items.get(target),
            msg=f"Unable to find target DNA '{target}' for well {self.identifier}.",
        )

    @classmethod
    def get_well_item_class(cls) -> type[WellItem]:
        return WellItem

    @classmethod
    def create(
        cls,
        reader: DesignQuantstudioReader,
        header: Header,
        well_data: pd.DataFrame,
        identifier: int,
    ) -> Well:
        well_item_class = cls.get_well_item_class()
        well_items = {
            SeriesData(item_data)[str, "Target"]: well_item_class.create(
                reader,
                SeriesData(item_data),
            )
            for _, item_data in well_data.iterrows()
        }
        multi_data = reader.get_non_empty_sheet_or_none("Multicomponent")
        return Well(
            identifier=identifier,
            items=well_items,
            multicomponent_data=(
                None
                if multi_data is None
                else create_multicomponent_data(header, multi_data, identifier)
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

    @classmethod
    def get_well_class(cls) -> type[Well]:
        return Well

    @classmethod
    def get_data_sheet(cls) -> str:
        return "Results"

    @classmethod
    def _add_data(
        cls, data: pd.DataFrame, extra_data: pd.DataFrame, columns: list[str]
    ) -> pd.DataFrame:
        new_data = data.copy()
        new_data[columns] = None
        for _, row in extra_data.iterrows():
            sample_cond = new_data["Sample"] == row["Sample"]
            target_cond = new_data["Target"] == row["Target"]
            new_data.loc[sample_cond & target_cond, columns] = row[columns].to_list()
        return new_data

    @classmethod
    def get_well_result_data(cls, reader: DesignQuantstudioReader) -> pd.DataFrame:
        return reader.get_non_empty_sheet(cls.get_data_sheet())

    @classmethod
    def create(
        cls,
        reader: DesignQuantstudioReader,
        header: Header,
    ) -> WellList:
        results_data = cls.get_well_result_data(reader)
        assert_df_column(results_data, "Well")

        well_class = cls.get_well_class()
        return WellList(
            wells=[
                well_class.create(
                    reader,
                    header,
                    well_data,
                    try_int(str(identifier), "well identifier"),
                )
                for identifier, well_data in results_data.groupby("Well")
            ]
        )


def create_amplification_data(
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
        msg=f"Unable to find amplification data for target '{target_dna_description}' in well {well_item_id}.",
    )

    cycle_number = assert_df_column(target_data, "Cycle Number")
    return AmplificationData(
        total_cycle_number_setting=try_float(str(cycle_number.max()), "Cycle Number"),
        cycle=cycle_number.tolist(),
        rn=assert_df_column(target_data, "Rn").tolist(),
        delta_rn=assert_df_column(target_data, "dRn").tolist(),
    )


def create_multicomponent_data(
    header: Header, data: pd.DataFrame, well_id: int
) -> MulticomponentData:
    well_data = assert_not_empty_df(
        data[assert_df_column(data, "Well") == well_id],
        msg=f"Unable to find multi component data for well {well_id}.",
    )

    stage_number = well_data.get("Stage Number")
    stage_data = (
        well_data
        if header.pcr_stage_number is None
        or stage_number is None
        or well_data["Stage Number"].isnull().all()
        else assert_not_empty_df(
            well_data[stage_number == header.pcr_stage_number],  # type: ignore[arg-type]
            msg=f"Unable to find multi component data for stage {header.pcr_stage_number}.",
        )
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
    fluorescence: list[float | None]
    derivative: list[float | None]

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
    cycle_threshold_result: float | None
    automatic_cycle_threshold_enabled_setting: bool | None
    automatic_baseline_determination_enabled_setting: bool | None
    normalized_reporter_result: float | None
    baseline_corrected_reporter_result: float | None
    baseline_determination_start_cycle_setting: int | None
    baseline_determination_end_cycle_setting: int | None
    genotyping_determination_result: str | None
    genotyping_determination_method_setting: float | None
    quantity: float | None
    quantity_mean: float | None
    quantity_sd: float | None
    ct_mean: float | None
    eq_ct_mean: float | None
    adj_eq_ct_mean: float | None
    ct_sd: float | None
    ct_se: float | None
    delta_ct_mean: float | None
    delta_ct_se: float | None
    delta_ct_sd: float | None
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
    amp_score: float | None
    cq_conf: float | None

    @classmethod
    def get_genotyping_determination_result(cls, _: SeriesData) -> str | None:
        return None

    @classmethod
    def get_genotyping_determination_method_setting(cls, _: SeriesData) -> float | None:
        return None

    @staticmethod
    def get_reference_sample(reader: DesignQuantstudioReader) -> str:
        data = reader.get_non_empty_sheet("RQ Replicate Group Result")
        reference_data = data[assert_df_column(data, "Rq") == 1]
        reference_sample_array = assert_df_column(reference_data, "Sample").unique()

        if reference_sample_array.size != 1:
            msg = "Unable to infer reference sample, expecting a single row in sheet 'RQ Replicate Group Result' to have Rq == 1."
            raise AllotropeConversionError(msg)

        return str(reference_sample_array[0])

    @staticmethod
    def get_reference_target(reader: DesignQuantstudioReader) -> str | None:
        data = reader.get_non_empty_sheet("RQ Replicate Group Result")

        possible_ref_targets = set.intersection(
            *[
                set(
                    assert_df_column(
                        sample_data[assert_df_column(sample_data, "Rq").isnull()],
                        "Target",
                    ).tolist()
                )
                for _, sample_data in data.groupby("Sample")
            ]
        )

        if len(possible_ref_targets) == 0:
            return None

        if len(possible_ref_targets) == 1:
            return str(possible_ref_targets.pop())

        msg = "Unable to infer reference target, expecting a single unique value for Target in sheet 'RQ Replicate Group Result' where Rq is empty."
        raise AllotropeConversionError(msg)

    @classmethod
    def create(
        cls,
        target_data: SeriesData,
        well_item_id: int,
    ) -> Result:
        return Result(
            cycle_threshold_value_setting=target_data[
                float,
                "Threshold",
                f"Unable to find cycle threshold value setting for well {well_item_id}",
            ],
            cycle_threshold_result=target_data.get(float, "Cq"),
            automatic_cycle_threshold_enabled_setting=target_data.get(
                bool, "Auto Threshold", None
            ),
            automatic_baseline_determination_enabled_setting=target_data.get(
                bool, "Auto Baseline", None
            ),
            normalized_reporter_result=target_data.get(float, "Rn"),
            baseline_corrected_reporter_result=target_data.get(float, "Delta Rn"),
            baseline_determination_start_cycle_setting=target_data.get(
                int, "Baseline Start"
            ),
            baseline_determination_end_cycle_setting=target_data.get(
                int, "Baseline End"
            ),
            genotyping_determination_result=cls.get_genotyping_determination_result(
                target_data
            ),
            genotyping_determination_method_setting=cls.get_genotyping_determination_method_setting(
                target_data
            ),
            quantity=target_data.get(float, "Quantity"),
            quantity_mean=target_data.get(float, "Quantity Mean"),
            quantity_sd=target_data.get(float, "Quantity SD"),
            ct_mean=target_data.get(float, "Cq Mean"),
            eq_ct_mean=target_data.get(float, "EqCq Mean"),
            adj_eq_ct_mean=target_data.get(float, "Adjusted EqCq Mean"),
            ct_sd=target_data.get(float, "Cq SD"),
            ct_se=target_data.get(float, "Cq SE"),
            delta_ct_mean=target_data.get(float, "Delta EqCq Mean"),
            delta_ct_se=target_data.get(float, "Delta EqCq SE"),
            delta_ct_sd=target_data.get(float, "Delta EqCq SD"),
            delta_delta_ct=target_data.get(float, "Delta Delta EqCq"),
            rq=target_data.get(float, "Rq"),
            rq_min=target_data.get(float, "Rq Min"),
            rq_max=target_data.get(float, "Rq Max"),
            rn_mean=target_data.get(float, "Rn Mean"),
            rn_sd=target_data.get(float, "Rn SD"),
            y_intercept=target_data.get(float, "Y-Intercept"),
            r_squared=target_data.get(float, "R2"),
            slope=target_data.get(float, "Slope"),
            efficiency=target_data.get(float, "Efficiency"),
            amp_score=target_data.get(float, "Amp Score"),
            cq_conf=target_data.get(float, "Cq Confidence"),
        )


@dataclass(frozen=True)
class Data:
    header: Header
    wells: WellList
    experiment_type: ExperimentType
    calculated_documents: list[CalculatedDocument]
    reference_target: str | None
    reference_sample: str | None

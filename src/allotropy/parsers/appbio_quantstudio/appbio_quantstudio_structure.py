from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any, TypeVar

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import SampleRoleType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_reader import (
    AppBioQuantStudioReader,
)
from allotropy.parsers.appbio_quantstudio.constants import (
    ExperimentType,
    SAMPLE_ROLE_TYPES_MAP,
)
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.utils.calculated_data_documents.definition import Referenceable
from allotropy.parsers.utils.pandas import df_to_series_data, map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_int

T = TypeVar("T")


def map_wells(map_func: Callable[..., T], data: pd.DataFrame) -> dict[int, T]:
    return {
        try_int(str(well_id), "well id"): map_func(well_data)
        for well_id, well_data in data.groupby("Well")
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
    plate_well_count: int | None
    experiment_type: ExperimentType
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    pcr_detection_chemistry: str | None
    passive_reference_dye_setting: str | None
    barcode: str | None
    analyst: str | None
    experimental_data_identifier: str
    well_volume: float

    @staticmethod
    def create(data: SeriesData) -> Header:
        experiments_type_options = {
            "Standard Curve": ExperimentType.standard_curve_qpcr_experiment,
            "Relative Standard Curve": ExperimentType.relative_standard_curve_qpcr_experiment,
            "Comparative Cт (ΔΔCт)": ExperimentType.comparative_ct_qpcr_experiment,
            "Melt Curve": ExperimentType.melt_curve_qpcr_experiment,
            "Genotyping": ExperimentType.genotyping_qpcr_experiment,
            "Presence/Absence": ExperimentType.presence_absence_qpcr_experiment,
        }

        plate_well_count = None
        block_type = data.get(str, "Block Type")
        if block_type:
            plate_well_count_search = re.search("(96)|(384)", block_type)
            if plate_well_count_search:
                plate_well_count = int(plate_well_count_search.group())

        return Header(
            measurement_time=data[str, "Experiment Run End Time"],
            plate_well_count=plate_well_count,
            experiment_type=assert_not_none(
                experiments_type_options.get(
                    data[str, "Experiment Type"].strip(),
                ),
                msg="Unable to find valid experiment type",
            ),
            device_identifier=(data.get(str, "Instrument Name", NOT_APPLICABLE)),
            model_number=data[str, "Instrument Type"],
            device_serial_number=data.get(
                str, "Instrument Serial Number", NOT_APPLICABLE
            ),
            measurement_method_identifier=data[str, "Quantification Cycle Method"],
            pcr_detection_chemistry=data.get(str, "Chemistry"),
            passive_reference_dye_setting=data.get(str, "Passive Reference"),
            barcode=data.get(str, "Experiment Barcode"),
            analyst=data.get(str, "Experiment User Name"),
            experimental_data_identifier=data[str, "Experiment Name"],
            well_volume=get_well_volume(block_type) if block_type else NEGATIVE_ZERO,
        )


@dataclass
class WellItem(Referenceable):
    identifier: int
    target_dna_description: str
    sample_identifier: str
    location_identifier: str
    reporter_dye_setting: str | None = None
    position: str | None = None
    well_location_identifier: str | None = None
    quencher_dye_setting: str | None = None
    sample_role_type: SampleRoleType | None = None
    group_identifier: str | None = None
    extra_data: dict[str, Any] | None = None
    _result: Result | None = None

    # Make hashable to allow for use of caching
    def __hash__(self) -> int:
        return hash(self.identifier)

    @property
    def has_result(self) -> bool:
        return self._result is not None

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
                location_identifier=data[str, "Well"],
                well_location_identifier=data.get(str, "Well Position"),
                quencher_dye_setting=data.get(str, "Quencher"),
                group_identifier=data.get(str, "Biogroup Name"),
                sample_role_type=SAMPLE_ROLE_TYPES_MAP.get(data.get(str, "Task", "")),
                extra_data={
                    "well identifier": identifier,
                    "sample color": data.get(str, "Sample Color"),
                    "biogroup color": data.get(str, "Biogroup Color"),
                    "target color": data.get(str, "Target Color"),
                },
            ),
            WellItem(
                uuid=random_uuid_str(),
                identifier=identifier,
                target_dna_description=f"{snp_name}-{allele2}",
                sample_identifier=data.get(str, "Sample Name", NOT_APPLICABLE),
                reporter_dye_setting=data.get(str, "Allele2 Reporter"),
                position=data.get(str, "Well Position", NOT_APPLICABLE),
                location_identifier=data[str, "Well"],
                well_location_identifier=data.get(str, "Well Position"),
                quencher_dye_setting=data.get(str, "Quencher"),
                group_identifier=data.get(str, "Biogroup Name"),
                sample_role_type=SAMPLE_ROLE_TYPES_MAP.get(data.get(str, "Task", "")),
                extra_data={
                    "well identifier": identifier,
                    "sample color": data.get(str, "Sample Color"),
                    "biogroup color": data.get(str, "Biogroup Color"),
                    "target color": data.get(str, "Target Color"),
                },
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
            location_identifier=data[str, "Well"],
            well_location_identifier=data.get(str, "Well Position"),
            quencher_dye_setting=data.get(str, "Quencher"),
            group_identifier=data.get(str, "Biogroup Name"),
            sample_role_type=SAMPLE_ROLE_TYPES_MAP.get(data.get(str, "Task", "")),
            extra_data={
                "well identifier": identifier,
                "sample color": data.get(str, "Sample Color"),
                "biogroup color": data.get(str, "Biogroup Color"),
                "target color": data.get(str, "Target Color"),
            },
        )


@dataclass
class Well:
    identifier: int
    items: list[WellItem]

    @staticmethod
    def create_genotyping(data: SeriesData) -> Well:
        return Well(
            identifier=try_int(str(data.series.name), "well id"),
            items=list(WellItem.create_genotyping(data)),
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
    def create(
        reader: AppBioQuantStudioReader, experiment_type: ExperimentType
    ) -> list[Well]:
        if (
            data := reader.sections.get("Sample Setup", reader.sections.get("Results"))
        ) is None:
            msg = "Expected 'Sample Setup' or 'Results' section"
            raise AllotropeConversionError(msg)

        if experiment_type == ExperimentType.genotyping_qpcr_experiment:
            return map_rows(data, Well.create_genotyping)
        else:
            return list(
                map_wells(
                    Well.create_generic, data[data["Target Name"].notnull()]
                ).values()
            )


@dataclass(frozen=True)
class AmplificationData:
    total_cycle_number_setting: float
    cycle: list[float]
    rn: list[float | None]
    delta_rn: list[float | None]


def create_amplification_data(
    reader: AppBioQuantStudioReader,
) -> dict[int, dict[str, AmplificationData]]:
    if (data := reader.sections.get("Amplification Data")) is None:
        return {}

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


def create_multicomponent_data(
    reader: AppBioQuantStudioReader,
) -> dict[int, MulticomponentData]:
    if (data := reader.sections.get("Multicomponent Data")) is None:
        return {}

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
            ExperimentType.comparative_ct_qpcr_experiment,
            ExperimentType.relative_standard_curve_qpcr_experiment,
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
    automatic_baseline: bool | None
    baseline_start: int | None
    baseline_end: int | None
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
    comments: str | None
    amp_score: float | None
    cq_conf: float | None
    extra_data: dict[str, Any] | None = None

    @staticmethod
    def create(
        reader: AppBioQuantStudioReader, experiment_type: ExperimentType
    ) -> tuple[dict[int, dict[str, Result]], ResultMetadata]:
        if (data := reader.sections.get("Results")) is None:
            msg = "Expected 'Results' section in file"
            raise AllotropeConversionError(msg)

        result = Result.create_results(data, experiment_type)
        metadata = SeriesData(pd.Series())
        if (raw_metadata := reader.sections.get("Results Metadata")) is not None:
            metadata = df_to_series_data(raw_metadata)

        return result, ResultMetadata.create(metadata, experiment_type)

    @staticmethod
    def create_results(
        data: pd.DataFrame, experiment_type: ExperimentType
    ) -> dict[int, dict[str, Result]]:
        target_key = "Target Name"
        if experiment_type == ExperimentType.genotyping_qpcr_experiment:
            target_key = "SNP Assay Name"

        def make_results(well_data: pd.DataFrame) -> dict[str, Result]:
            return {
                target_dna_description: result
                for target_id, target_data in well_data.groupby(target_key)
                for target_dna_description, result in Result.create_result(
                    df_to_series_data(target_data),
                    experiment_type,
                    str(target_id),
                ).items()
            }

        return map_wells(make_results, data)

    @staticmethod
    def create_result(
        data: SeriesData, experiment_type: ExperimentType, target_id: str
    ) -> dict[str, Result]:
        ct_col = Result.get_ct_col(list(data.series.index.astype(str)))
        ct_prefix = ct_col.capitalize()
        if experiment_type == ExperimentType.genotyping_qpcr_experiment:
            allele_prefixes = []
            for column in data.series.index:
                if match := re.match(rf"(^\w+) {ct_prefix}$", column):
                    allele_prefixes.append(f"{match.groups()[0]} ")
        else:
            allele_prefixes = [""]

        return {
            f"{target_id}{f'-{allele_prefix}' if allele_prefix else ''}".replace(
                " ", ""
            ): Result(
                cycle_threshold_value_setting=data[
                    float, f"{allele_prefix}{ct_prefix} Threshold"
                ],
                # TODO(nstender): really seems like this should be NaN if invalid value. Keeping to preserve tests.
                cycle_threshold_result=data.get(float, f"{allele_prefix}{ct_col}"),
                automatic_cycle_threshold_enabled_setting=data.get(
                    bool, f"{allele_prefix}Automatic {ct_prefix} Threshold"
                ),
                automatic_baseline=data.get(bool, f"{allele_prefix}Automatic Baseline"),
                baseline_start=data.get(int, f"{allele_prefix}Baseline Start"),
                baseline_end=data.get(int, f"{allele_prefix}Baseline End"),
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
                ct_mean=data.get(float, f"{ct_prefix} Mean"),
                ct_sd=data.get(float, f"{ct_prefix} SD"),
                delta_ct_mean=data.get(float, f"Delta {ct_prefix} Mean"),
                delta_ct_se=data.get(float, f"Delta {ct_prefix} SE"),
                delta_delta_ct=data.get(float, f"Delta Delta {ct_prefix}"),
                rq=data.get(float, "RQ"),
                rq_min=data.get(float, "RQ Min"),
                rq_max=data.get(float, "RQ Max"),
                rn_mean=data.get(float, "Rn Mean"),
                rn_sd=data.get(float, "Rn SD"),
                y_intercept=data.get(float, "Y-Intercept"),
                r_squared=data.get(float, "R(superscript 2)"),
                slope=data.get(float, "Slope"),
                efficiency=data.get(float, "Efficiency"),
                comments=data.get(str, "Comments"),
                amp_score=data.get(float, "Amp Score"),
                cq_conf=data.get(float, "Cq Conf"),
                extra_data={
                    "omit": data.get(bool, "Omit"),
                    "highsd": data.get(str, "HIGHSD"),
                    "noamp": data.get(str, "NOAMP"),
                    "expfail": data.get(str, "EXPFAIL"),
                    "tholdfail": data.get(str, "THOLDFAIL"),
                    "prfdrop": data.get(str, "PRFDROP"),
                },
            )
            for allele_prefix in allele_prefixes
        }

    @staticmethod
    def get_ct_col(columns: list[str]) -> str:
        """Looks for any column matching the pattern of the cycle threshhold.

        The pattern for the threshold column is `[allele prefix]<quantification_method>`
        where `allele prefix` is optional and `quantification_method` can be any of
        Ct, Crt or Cq with different capitalizations.

        This identifier is used as a prefix to all the cycle threshold related
        columns (always capitalized)
        """
        r = re.compile(r".*(C[tT]|C(?:rt|RT)|C[qQ])$")
        for column in columns:
            if match := r.match(column):
                return match.groups()[0]

        msg = "Unable to identify ct prefix"
        raise AllotropeConversionError(msg)


@dataclass(frozen=True)
class MeltCurveRawData:
    reading: list[float]
    fluorescence: list[float | None]
    derivative: list[float | None]

    @staticmethod
    def create(reader: AppBioQuantStudioReader) -> dict[int, MeltCurveRawData]:
        if (data := reader.sections.get("Melt Curve Raw Data")) is None:
            return {}

        def make_data(well_data: pd.Series[Any]) -> MeltCurveRawData:
            return MeltCurveRawData(
                reading=well_data["Reading"].tolist(),
                fluorescence=well_data["Fluorescence"].tolist(),
                derivative=well_data["Derivative"].tolist(),
            )

        return map_wells(make_data, data)

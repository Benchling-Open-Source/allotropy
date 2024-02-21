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

# from io import StringIO
import re
from typing import Optional
import uuid

# import numpy as np
import pandas as pd

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignAndAnalysisReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.referenceable import (
    Referenceable,
)
from allotropy.parsers.utils.values import (
    assert_not_empty_df,
    assert_not_none,
    df_to_series,
    try_bool_from_series_or_none,
    try_float_from_series,
    try_float_from_series_or_none,
    try_float_or_none,
    try_int,
    try_int_from_series,
    try_str_from_series,
    try_str_from_series_or_none,
)


@dataclass(frozen=True)
class Header:
    measurement_time: str
    plate_well_count: int
    experiment_type: ExperimentType
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    pcr_detection_chemistry: Optional[str]
    passive_reference_dye_setting: Optional[str]
    barcode: Optional[str]
    analyst: Optional[str]
    experimental_data_identifier: Optional[str]
    pcr_stage_number: int
    software_name: Optional[str]
    software_version: Optional[str]

    @staticmethod
    def create(reader: DesignAndAnalysisReader) -> Header:
        # lines = [line.replace("*", "", 1) for line in reader.pop_until(r"^\[.+\]")]
        # csv_stream = StringIO("\n".join(lines))
        # raw_data = pd.read_csv(
        #    csv_stream, header=None, sep="=", names=["index", "values"]
        # )
        # data = pd.Series(raw_data["values"].values, index=raw_data["index"])
        # data.index = data.index.str.strip()
        # data = data.str.strip().replace("NA", None)
        data = reader.metadata

        """experiments_type_options = {
            "Standard Curve": ExperimentType.standard_curve_qPCR_experiment,
            "Relative Standard Curve": ExperimentType.relative_standard_curve_qPCR_experiment,
            "Comparative Cт (ΔΔCт)": ExperimentType.comparative_CT_qPCR_experiment,
            "Melt Curve": ExperimentType.melt_curve_qPCR_experiment,
            "Genotyping": ExperimentType.genotyping_qPCR_experiment,
            "Presence/Absence": ExperimentType.presence_absence_qPCR_experiment,
        }"""

        return Header(
            measurement_time=try_str_from_series(data, "Run End Data/Time"),
            plate_well_count=assert_not_none(
                try_int(
                    assert_not_none(
                        re.match(
                            "(96)|(384)",
                            try_str_from_series(data, "Block Type"),
                        ),
                        msg="Unable to find plate well count",
                    ).group(),
                    "plate well count",
                ),
                msg="Unable to interpret plate well count",
            ),
            # experiment_type=assert_not_none(
            #    experiments_type_options.get(
            #        try_str_from_series(data, "Experiment Type"),
            #    ),
            #    msg="Unable to find valid experiment type",
            # ),
            # default to this for now as it's not in the data file
            experiment_type=ExperimentType.melt_curve_qPCR_experiment,
            device_identifier=(
                try_str_from_series_or_none(data, "Instrument Name") or "NA"
            ),
            model_number=try_str_from_series(data, "Instrument Type"),
            device_serial_number=try_str_from_series_or_none(
                data, "Instrument Serial Number"
            )
            or "NA",
            measurement_method_identifier=try_str_from_series(
                data, "Quantification Cycle Method"
            ),
            pcr_detection_chemistry=try_str_from_series_or_none(data, "Chemistry"),
            passive_reference_dye_setting=try_str_from_series_or_none(
                data, "Passive Reference"
            ),
            barcode=try_str_from_series_or_none(data, "Barcode"),
            analyst=try_str_from_series_or_none(data, "Operator"),
            experimental_data_identifier=try_str_from_series_or_none(
                data, "Experiment Name"
            ),
            pcr_stage_number=assert_not_none(
                try_int(
                    assert_not_none(
                        re.match(
                            r"(Stage )(\d+)",
                            try_str_from_series(data, r"PCR Stage/Step Number"),
                        ),
                        msg="Unable to find PCR Stage Number",
                    ).group(2),
                    "PCR Stage Number",
                ),
                msg=r"Unable to interpret PCR Stage/Step Number",
            ),
            software_name=try_str_from_series(data, "Software Name and Version").split(
                " v"
            )[0],
            software_version=try_str_from_series(
                data, "Software Name and Version"
            ).split(" v")[1],
        )


@dataclass
class WellItem(Referenceable):
    uuid: str
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
    _melt_curve_raw_data: Optional[MeltCurveRawData] = None

    @property
    def melt_curve_raw_data(self) -> Optional[MeltCurveRawData]:
        return assert_not_none(
            self._melt_curve_raw_data,
            msg=f"Unable to find melt curve data for target '{self.target_dna_description}' in well {self.identifier} .",
        )

    @melt_curve_raw_data.setter
    def melt_curve_raw_data(self, melt_curve_raw_data: MeltCurveRawData) -> None:
        self._melt_curve_raw_data = melt_curve_raw_data

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
    def create_genotyping(data: pd.Series[str]) -> tuple[WellItem, WellItem]:
        identifier = try_int_from_series(data, "Well")

        snp_name = try_str_from_series(
            data,
            "SNP Assay Name",
            msg=f"Unable to find snp name for well {identifier}",
        )

        sample_identifier = try_str_from_series(
            data,
            "Sample Name",
            msg=f"Unable to find sample identifier for well {identifier}",
        )

        allele1 = try_str_from_series(
            data,
            "Allele1 Name",
            msg=f"Unable to find allele 1 for well {identifier}",
        )

        allele2 = try_str_from_series(
            data,
            "Allele2 Name",
            msg=f"Unable to find allele 2 for well {identifier}",
        )

        return (
            WellItem(
                uuid=str(uuid.uuid4()),
                identifier=identifier,
                target_dna_description=f"{snp_name}-{allele1}",
                sample_identifier=sample_identifier,
                reporter_dye_setting=try_str_from_series_or_none(
                    data, "Allele1 Reporter"
                ),
                position=try_str_from_series_or_none(data, "Well Position")
                or "UNDEFINED",
                well_location_identifier=try_str_from_series_or_none(
                    data, "Well Position"
                ),
                quencher_dye_setting=try_str_from_series_or_none(data, "Quencher"),
                sample_role_type=try_str_from_series_or_none(data, "Task"),
            ),
            WellItem(
                uuid=str(uuid.uuid4()),
                identifier=identifier,
                target_dna_description=f"{snp_name}-{allele2}",
                sample_identifier=sample_identifier,
                reporter_dye_setting=try_str_from_series_or_none(
                    data, "Allele2 Reporter"
                ),
                position=try_str_from_series_or_none(data, "Well Position")
                or "UNDEFINED",
                well_location_identifier=try_str_from_series_or_none(
                    data, "Well Position"
                ),
                quencher_dye_setting=try_str_from_series_or_none(data, "Quencher"),
                sample_role_type=try_str_from_series_or_none(data, "Task"),
            ),
        )

    @staticmethod
    def create_generic(data: pd.Series[str]) -> WellItem:
        identifier = try_int_from_series(data, "Well")

        target_dna_description = try_str_from_series(
            data,
            "Target",
            msg=f"Unable to find target dna description for well {identifier}",
        )

        sample_identifier = try_str_from_series(
            data,
            "Sample",
            msg=f"Unable to find sample identifier for well {identifier}",
        )

        return WellItem(
            uuid=str(uuid.uuid4()),
            identifier=identifier,
            target_dna_description=target_dna_description,
            sample_identifier=sample_identifier,
            reporter_dye_setting=try_str_from_series_or_none(data, "Reporter"),
            position=try_str_from_series_or_none(data, "Well Position") or "UNDEFINED",
            well_location_identifier=try_str_from_series_or_none(data, "Well Position"),
            quencher_dye_setting=try_str_from_series_or_none(data, "Quencher"),
            sample_role_type=try_str_from_series_or_none(data, "Task"),
        )


@dataclass
class Well:
    identifier: int
    items: dict[str, WellItem]
    _multicomponent_data: Optional[MulticomponentData] = None
    # _melt_curve_raw_data: Optional[MeltCurveRawData] = None

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

    """@property
    def melt_curve_raw_data(self) -> Optional[MeltCurveRawData]:
        return self._melt_curve_raw_data

    @melt_curve_raw_data.setter
    def melt_curve_raw_data(self, melt_curve_raw_data: MeltCurveRawData) -> None:
        self._melt_curve_raw_data = melt_curve_raw_data"""

    @staticmethod
    def create_genotyping(identifier: int, well_data: pd.Series[str]) -> Well:
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
                item_data["Target"]: WellItem.create_generic(item_data)
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
    def create(
        reader: DesignAndAnalysisReader, experiment_type: ExperimentType
    ) -> WellList:
        # assert_not_none(
        #    reader.drop_until(r"^\[Sample Setup\]"),
        #    msg="Unable to find 'Sample Setup' section in file.",
        # )

        # reader.pop()  # remove title
        # lines = list(reader.pop_until(r"^\[.+\]"))
        # csv_stream = StringIO("\n".join(lines))
        # raw_data = pd.read_csv(csv_stream, sep="\t").replace(np.nan, None)
        # data = raw_data[raw_data["Sample Name"].notnull()]

        assert_not_empty_df(
            reader.data["Results"],
            msg="Unable to find 'Results' sheet in file.",
        )

        raw_data = reader.data["Results"]
        data = raw_data[raw_data["Sample"].notnull()]

        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return WellList(
                [
                    Well.create_genotyping(
                        try_int(str(identifier), "genotyping well identifier"),
                        well_data,
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
                for identifier, well_data in data.groupby("Well")
            ]
        )


@dataclass(frozen=True)
class AmplificationData:
    total_cycle_number_setting: float
    cycle: list[float]
    rn: list[Optional[float]]
    delta_rn: list[Optional[float]]

    @staticmethod
    def get_data(reader: DesignAndAnalysisReader) -> pd.DataFrame:
        # assert_not_none(
        #    reader.drop_until(r"^\[Amplification Data\]"),
        #    msg="Unable to find 'Amplification Data' section in file.",
        # )

        # reader.pop()  # remove title
        # lines = list(reader.pop_until(r"^\[.+\]"))
        # csv_stream = StringIO("\n".join(lines))
        # return pd.read_csv(csv_stream, sep="\t", thousands=r",")

        assert_not_empty_df(
            reader.data["Amplification Data"],
            msg="Unable to find 'Amplification Data' sheet in file.",
        )
        return reader.data["Amplification Data"]

    @staticmethod
    def create(
        amplification_data: pd.DataFrame, well_item: WellItem
    ) -> AmplificationData:
        well_data = assert_not_empty_df(
            amplification_data[amplification_data["Well"] == well_item.identifier],
            msg=f"Unable to find amplification data for well {well_item.identifier}.",
        )

        target_data = assert_not_empty_df(
            well_data[well_data["Target"] == well_item.target_dna_description],
            msg=f"Unable to find amplification data for target '{well_item.target_dna_description}' in well {well_item.identifier} .",
        )

        return AmplificationData(
            total_cycle_number_setting=float(target_data["Cycle Number"].max()),
            cycle=target_data["Cycle Number"].tolist(),
            rn=target_data["Rn"].tolist(),
            delta_rn=target_data["dRn"].tolist(),
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
    def get_data(reader: DesignAndAnalysisReader) -> Optional[pd.DataFrame]:
        # if not reader.match(r"^\[Multicomponent Data\]"):
        #    return None
        # reader.pop()  # remove title
        # lines = list(reader.pop_until(r"^\[.+\]"))
        # csv_stream = StringIO("\n".join(lines))
        # return pd.read_csv(csv_stream, sep="\t", thousands=r",")

        if "Multicomponent" in reader.data:
            if not reader.data["Multicomponent"].empty:
                return reader.data["Multicomponent"]
        return None

    @staticmethod
    def create(data: pd.DataFrame, well: Well, header: Header) -> MulticomponentData:
        well_data = assert_not_empty_df(
            data[data["Well"] == well.identifier],
            msg=f"Unable to find multi component data for well {well.identifier}.",
        )

        stage_data = assert_not_empty_df(
            well_data[well_data["Stage Number"] == header.pcr_stage_number],
            msg=f"Unable to find multi component data for stage {header.pcr_stage_number}.",
        )

        return MulticomponentData(
            cycle=stage_data["Cycle Number"].tolist(),
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
class Result:
    cycle_threshold_value_setting: float
    cycle_threshold_result: Optional[float]
    automatic_cycle_threshold_enabled_setting: Optional[bool]
    automatic_baseline_determination_enabled_setting: Optional[bool]
    normalized_reporter_result: Optional[float]
    baseline_corrected_reporter_result: Optional[float]
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
    def get_data(
        reader: DesignAndAnalysisReader,
    ) -> tuple[pd.DataFrame, pd.Series[str]]:
        # assert_not_none(
        #    reader.drop_until(r"^\[Results\]"),
        #    msg="Unable to find 'Results' section in file.",
        # )

        # reader.pop()  # remove title
        # data_lines = list(reader.pop_until_empty())
        # csv_stream = StringIO("\n".join(data_lines))
        # data = pd.read_csv(csv_stream, sep="\t", thousands=r",").replace(np.nan, None)

        # reader.drop_empty()

        # if reader.match(r"\[.+\]"):
        #    return data, pd.Series()

        # metadata_lines = list(reader.pop_until_empty())
        # csv_stream = StringIO("\n".join(metadata_lines))
        # raw_data = pd.read_csv(
        #    csv_stream, header=None, sep="=", names=["index", "values"]
        # )
        # metadata = pd.Series(raw_data["values"].values, index=raw_data["index"])
        # metadata.index = metadata.index.str.strip()

        # reader.drop_empty()

        # return data, metadata.str.strip()
        # The example I have doesn't have this metadata, so returning an empty Series for now)
        return reader.data["Results"], pd.Series()

    @staticmethod
    def create_genotyping(data: pd.DataFrame, well_item: WellItem) -> Result:
        well_data = assert_not_empty_df(
            data[data["Well"] == well_item.identifier],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        snp_assay_name, _ = well_item.target_dna_description.split("-")
        target_data = df_to_series(
            assert_not_empty_df(
                well_data[well_data["SNP Assay Name"] == snp_assay_name],
                msg=f"Unable to find result data for well {well_item.identifier}.",
            ),
            msg=f"Expected exactly 1 row of results to be associated with target '{well_item.target_dna_description}' in well {well_item.identifier}.",
        )

        _, raw_allele = well_item.target_dna_description.split("-")
        allele = raw_allele.replace(" ", "")
        cycle_threshold_value_setting = try_float_from_series(
            target_data,
            f"{allele} Ct Threshold",
            msg=f"Unable to find cycle threshold value setting for well {well_item.identifier}",
        )

        cycle_threshold_result = assert_not_none(
            target_data.get(f"{allele} Ct"),
            msg="Unable to find cycle threshold result",
        )

        return Result(
            cycle_threshold_value_setting=cycle_threshold_value_setting,
            cycle_threshold_result=try_float_or_none(str(cycle_threshold_result)),
            automatic_cycle_threshold_enabled_setting=try_bool_from_series_or_none(
                target_data, f"{allele} Automatic Ct Threshold"
            ),
            automatic_baseline_determination_enabled_setting=try_bool_from_series_or_none(
                target_data, f"{allele} Automatic Baseline"
            ),
            normalized_reporter_result=try_float_from_series_or_none(target_data, "Rn"),
            baseline_corrected_reporter_result=try_float_from_series_or_none(
                target_data, f"{allele} Delta Rn"
            ),
            genotyping_determination_result=try_str_from_series_or_none(
                target_data, "Call"
            ),
            genotyping_determination_method_setting=try_float_from_series_or_none(
                target_data, "Threshold Value"
            ),
            quantity=try_float_from_series_or_none(target_data, "Quantity"),
            quantity_mean=try_float_from_series_or_none(target_data, "Quantity Mean"),
            quantity_sd=try_float_from_series_or_none(target_data, "Quantity SD"),
            ct_mean=try_float_from_series_or_none(target_data, "Ct Mean"),
            ct_sd=try_float_from_series_or_none(target_data, "Ct SD"),
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

    @staticmethod
    def create_generic(data: pd.DataFrame, well_item: WellItem) -> Result:
        well_data = assert_not_empty_df(
            data[data["Well"] == well_item.identifier],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        target_data = df_to_series(
            assert_not_empty_df(
                well_data[well_data["Target"] == well_item.target_dna_description],
                msg=f"Unable to find result data for well {well_item.identifier}.",
            ),
            msg=f"Expected exactly 1 row of results to be associated with target '{well_item.target_dna_description}' in well {well_item.identifier}.",
        )

        cycle_threshold_result = assert_not_none(
            target_data.get("Cq"),
            msg="Unable to find cycle threshold result",
        )

        return Result(
            cycle_threshold_value_setting=try_float_from_series(
                target_data,
                "Threshold",
                msg=f"Unable to find cycle threshold value setting for well {well_item.identifier}",
            ),
            cycle_threshold_result=try_float_or_none(str(cycle_threshold_result)),
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
            genotyping_determination_result=try_str_from_series_or_none(
                target_data, "Call"
            ),
            genotyping_determination_method_setting=try_float_from_series_or_none(
                target_data, "Threshold"
            ),
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
    fluorescence: list[Optional[float]]
    derivative: list[Optional[float]]

    @staticmethod
    def create(data: pd.DataFrame, well_item: WellItem) -> MeltCurveRawData:
        well_data = assert_not_empty_df(
            data[data["Well"] == well_item.identifier],
            msg=f"Unable to find Melt Curve Raw data for well {well_item.identifier}.",
        )

        target_data = assert_not_empty_df(
            well_data[well_data["Target"] == well_item.target_dna_description],
            msg=f"Unable to find Melt Curve Raw data for target '{well_item.target_dna_description}' in well {well_item.identifier} .",
        )

        return MeltCurveRawData(
            reading=target_data["Temperature"].tolist(),
            fluorescence=target_data["Fluorescence"].tolist(),
            derivative=target_data["Derivative"].tolist(),
        )

    @staticmethod
    def get_data(reader: DesignAndAnalysisReader) -> Optional[pd.DataFrame]:
        # if not reader.match(r"^\[Melt Curve Raw Data\]"):
        #    return None
        # reader.pop()  # remove title
        # lines = list(reader.pop_until_empty())
        # csv_stream = StringIO("\n".join(lines))
        # return pd.read_csv(csv_stream, sep="\t", thousands=r",")
        assert_not_empty_df(
            reader.data["Melt Curve Raw"],
            msg="Unable to find 'Melt Curve Raw' sheet in file.",
        )
        return reader.data["Melt Curve Raw"]


@dataclass(frozen=True)
class Data:
    header: Header
    wells: WellList
    endogenous_control: str
    reference_sample: str

    @staticmethod
    def create(reader: DesignAndAnalysisReader) -> Data:
        header = Header.create(reader)
        wells = WellList.create(reader, header.experiment_type)

        amp_data = AmplificationData.get_data(reader)
        multi_data = MulticomponentData.get_data(reader)
        results_data, results_metadata = Result.get_data(reader)
        melt_data = MeltCurveRawData.get_data(reader)
        for well in wells:
            if multi_data is not None:
                well.multicomponent_data = MulticomponentData.create(
                    multi_data, well, header
                )

            if melt_data:
                for well_item in well.items.values():
                    well_item.melt_curve_raw_data = MeltCurveRawData.create(
                        melt_data,
                        well_item,
                    )

            for well_item in well.items.values():
                well_item.amplification_data = AmplificationData.create(
                    amp_data,
                    well_item,
                )

                well_item.result = Result.create(
                    results_data,
                    well_item,
                    header.experiment_type,
                )

        endogenous_control = (
            try_str_from_series_or_none(results_metadata, "Endogenous Control") or ""
        )
        reference_sample = (
            try_str_from_series_or_none(results_metadata, "Reference Sample") or ""
        )

        return Data(
            header,
            wells,
            endogenous_control,
            reference_sample,
        )

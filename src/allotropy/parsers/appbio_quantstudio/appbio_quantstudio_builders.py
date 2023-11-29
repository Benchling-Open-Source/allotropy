# mypy: disallow_any_generics = False

from io import StringIO
from typing import Optional

import numpy as np
import pandas as pd

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import (
    ExperimentType,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_calculated_documents import (
    build_quantity,
    iter_calculated_data_documents,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Data,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    RawData,
    Result,
    Well,
    WellItem,
    WellList,
)
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import (
    assert_not_empty_df,
    assert_not_none,
    df_to_series,
    try_bool_from_series_or_none,
    try_float_from_series,
    try_float_from_series_or_none,
    try_float_or_none,
    try_str_from_series_or_none,
)


class MulticomponentDataBuilder:
    @staticmethod
    def build(data: pd.DataFrame, well: Well) -> MulticomponentData:
        well_data = MulticomponentDataBuilder.filter_well_data(data, well)
        return MulticomponentData(
            cycle=well_data["Cycle"].tolist(),
            columns={
                name: well_data[name].tolist()  # type: ignore[misc]
                for name in well_data
                if name not in ["Well", "Cycle", "Well Position"]
            },
        )

    @staticmethod
    def filter_well_data(data: pd.DataFrame, well: Well) -> pd.DataFrame:
        return assert_not_empty_df(
            data[data["Well"] == well.identifier],
            msg=f"Unable to find multi component data for well {well.identifier}.",
        )

    @staticmethod
    def get_data(reader: LinesReader) -> Optional[pd.DataFrame]:
        if not reader.match(r"^\[Multicomponent Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t", thousands=r",")


class GenericResultsBuilder:
    @staticmethod
    def build(data: pd.DataFrame, well_item: WellItem) -> Result:
        target_data = GenericResultsBuilder.filter_target_data(data, well_item)
        cycle_threshold_value_setting = try_float_from_series(
            target_data,
            "Ct Threshold",
            msg=f"Unable to find cycle threshold value setting for well {well_item.identifier}",
        )

        cycle_threshold_result = assert_not_none(
            target_data.get("CT"),
            msg="Unable to find cycle threshold result",
        )

        return Result(
            cycle_threshold_value_setting=cycle_threshold_value_setting,
            cycle_threshold_result=try_float_or_none(str(cycle_threshold_result)),
            automatic_cycle_threshold_enabled_setting=try_bool_from_series_or_none(
                target_data, "Automatic Ct Threshold"
            ),
            automatic_baseline_determination_enabled_setting=try_bool_from_series_or_none(
                target_data, "Automatic Baseline"
            ),
            normalized_reporter_result=try_float_from_series_or_none(target_data, "Rn"),
            baseline_corrected_reporter_result=try_float_from_series_or_none(
                target_data, "Delta Rn"
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
    def filter_target_data(data: pd.DataFrame, well_item: WellItem) -> pd.Series:
        well_data = assert_not_empty_df(
            data[data["Well"] == well_item.identifier],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        target_data = assert_not_empty_df(
            well_data[well_data["Target Name"] == well_item.target_dna_description],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        return df_to_series(
            target_data,
            f"Expected exactly 1 row of results to be associated to well {well_item.identifier}.",
        )


class GenotypingResultsBuilder:
    @staticmethod
    def build(data: pd.DataFrame, well_item: WellItem) -> Result:
        target_data = GenotypingResultsBuilder.filter_target_data(data, well_item)
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
    def filter_target_data(data: pd.DataFrame, well_item: WellItem) -> pd.Series:
        well_data = assert_not_empty_df(
            data[data["Well"] == well_item.identifier],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        snp_assay_name, _ = well_item.target_dna_description.split("-")
        target_data = assert_not_empty_df(
            well_data[well_data["SNP Assay Name"] == snp_assay_name],
            msg=f"Unable to find result data for well {well_item.identifier}.",
        )

        return df_to_series(
            target_data,
            msg=f"Expected exactly 1 row of results to be associated to well {well_item.identifier}.",
        )


class ResultsBuilder:
    @staticmethod
    def build(
        data: pd.DataFrame, well_item: WellItem, experiment_type: ExperimentType
    ) -> Result:
        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return GenotypingResultsBuilder.build(data, well_item)
        return GenericResultsBuilder.build(data, well_item)

    @staticmethod
    def get_data(reader: LinesReader) -> tuple[pd.DataFrame, pd.Series]:
        if reader.drop_until(r"^\[Results\]") is None:
            msg = "Unable to find 'Results' section in file."
            raise AllotropeConversionError(msg)

        reader.pop()  # remove title
        data_lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(data_lines))
        data = pd.read_csv(csv_stream, sep="\t", thousands=r",").replace(np.nan, None)

        reader.drop_empty()

        if reader.match(r"\[.+\]"):
            return data, pd.Series()

        metadata_lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(metadata_lines))
        raw_data = pd.read_csv(
            csv_stream, header=None, sep="=", names=["index", "values"]
        )
        metadata = pd.Series(raw_data["values"].values, index=raw_data["index"])
        metadata.index = metadata.index.str.strip()

        reader.drop_empty()

        return data, metadata.str.strip()


class MeltCurveRawDataBuilder:
    @staticmethod
    def build(data: pd.DataFrame, well: Well) -> MeltCurveRawData:
        well_data = MeltCurveRawDataBuilder.filter_well_data(data, well)
        return MeltCurveRawData(
            reading=well_data["Reading"].tolist(),
            fluorescence=well_data["Fluorescence"].tolist(),
            derivative=well_data["Derivative"].tolist(),
        )

    @staticmethod
    def filter_well_data(data: pd.DataFrame, well: Well) -> pd.DataFrame:
        return assert_not_empty_df(
            data[data["Well"] == well.identifier],
            msg=f"Unable to find melt curve raw data for well {well.identifier}.",
        )

    @staticmethod
    def get_data(reader: LinesReader) -> Optional[pd.DataFrame]:
        if not reader.match(r"^\[Melt Curve Raw Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t", thousands=r",")


class DataBuilder:
    @staticmethod
    def build(reader: LinesReader) -> Data:
        header = Header.create(reader)
        wells = WellList.create(reader, header.experiment_type)
        raw_data = RawData.create(reader)

        amp_data = AmplificationData.get_data(reader)
        multi_data = MulticomponentDataBuilder.get_data(reader)
        results_data, results_metadata = ResultsBuilder.get_data(reader)
        melt_data = MeltCurveRawDataBuilder.get_data(reader)
        for well in wells:
            if multi_data is not None:
                well.multicomponent_data = MulticomponentDataBuilder.build(
                    multi_data,
                    well,
                )

            if melt_data is not None:
                well.melt_curve_raw_data = MeltCurveRawDataBuilder.build(
                    melt_data,
                    well,
                )

            for well_item in well.items.values():
                well_item.amplification_data = AmplificationData.create(
                    amp_data,
                    well_item,
                )

                well_item.result = ResultsBuilder.build(
                    results_data,
                    well_item,
                    header.experiment_type,
                )

            if an_well_item := well.get_an_well_item():
                well.calculated_document = build_quantity(an_well_item)

        endogenous_control = (
            try_str_from_series_or_none(results_metadata, "Endogenous Control") or ""
        )
        reference_sample = (
            try_str_from_series_or_none(results_metadata, "Reference Sample") or ""
        )

        return Data(
            header,
            wells,
            raw_data,
            endogenous_control,
            reference_sample,
            list(
                iter_calculated_data_documents(
                    wells,
                    header.experiment_type,
                    reference_sample,
                    endogenous_control,
                )
            ),
        )

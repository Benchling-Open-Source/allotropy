from io import StringIO
from typing import Any, Optional

import numpy as np
import pandas as pd

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import (
    ExperimentType,
)
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


def df_to_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(df.iloc[0], index=df.columns)


def float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def get_str(data: pd.Series, key: str, default: Optional[str] = None) -> Optional[str]:
    value = data.get(key, default)
    return None if value is None else str(value)


def get_float(data: pd.Series, key: str) -> Optional[float]:
    try:
        value = data.get(key)
        return float_or_none(value)
    except Exception as e:
        msg = f"Unable to convert {key} to float value"
        raise AllotropeConversionError(msg) from e


def get_bool(data: pd.Series, key: str) -> Optional[bool]:
    try:
        value = data.get(key)
        return None if value is None else bool(value)
    except Exception as e:
        msg = f"Unable to convert {key} to bool value"
        raise AllotropeConversionError(msg) from e


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
        well_data = data[data["Well"] == well.identifier]
        if well_data.empty:
            msg = f"Unable to find multi component data for well {well.identifier}"
            raise AllotropeConversionError(msg)

        return well_data

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
        cycle_threshold_value_setting = get_float(target_data, "Ct Threshold")
        if cycle_threshold_value_setting is None:
            msg = "Unable to get cycle threshold value setting"
            raise AllotropeConversionError(msg)

        cycle_threshold_result = target_data.get("CT")
        if cycle_threshold_result is None:
            msg = "Unable to get cycle threshold result"
            raise AllotropeConversionError(msg)

        return Result(
            cycle_threshold_value_setting=cycle_threshold_value_setting,
            cycle_threshold_result=float_or_none(cycle_threshold_result),
            automatic_cycle_threshold_enabled_setting=get_bool(
                target_data, "Automatic Ct Threshold"
            ),
            automatic_baseline_determination_enabled_setting=get_bool(
                target_data, "Automatic Baseline"
            ),
            normalized_reporter_result=get_float(target_data, "Rn"),
            baseline_corrected_reporter_result=get_float(target_data, "Delta Rn"),
            genotyping_determination_result=get_str(target_data, "Call"),
            genotyping_determination_method_setting=get_float(
                target_data, "Threshold Value"
            ),
            quantity=get_float(target_data, "Quantity"),
            quantity_mean=get_float(target_data, "Quantity Mean"),
            quantity_sd=get_float(target_data, "Quantity SD"),
            ct_mean=get_float(target_data, "Ct Mean"),
            ct_sd=get_float(target_data, "Ct SD"),
            delta_ct_mean=get_float(target_data, "Delta Ct Mean"),
            delta_ct_se=get_float(target_data, "Delta Ct SE"),
            delta_delta_ct=get_float(target_data, "Delta Delta Ct"),
            rq=get_float(target_data, "RQ"),
            rq_min=get_float(target_data, "RQ Min"),
            rq_max=get_float(target_data, "RQ Max"),
            rn_mean=get_float(target_data, "Rn Mean"),
            rn_sd=get_float(target_data, "Rn SD"),
            y_intercept=get_float(target_data, "Y-Intercept"),
            r_squared=get_float(target_data, "R(superscript 2)"),
            slope=get_float(target_data, "Slope"),
            efficiency=get_float(target_data, "Efficiency"),
        )

    @staticmethod
    def filter_target_data(data: pd.DataFrame, well_item: WellItem) -> pd.Series:
        well_data = data[data["Well"] == well_item.identifier]
        if well_data.empty:
            msg = f"Unable to get result data for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        target_data = well_data[
            well_data["Target Name"] == well_item.target_dna_description
        ]
        if target_data.empty:
            msg = f"Unable to get result data for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        n_rows, _ = target_data.shape
        if n_rows != 1:
            msg = f"Unexpected number of results associated to well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        return df_to_series(target_data)


class GenotypingResultsBuilder:
    @staticmethod
    def build(data: pd.DataFrame, well_item: WellItem) -> Result:
        target_data = GenotypingResultsBuilder.filter_target_data(data, well_item)
        _, raw_allele = well_item.target_dna_description.split("-")
        allele = raw_allele.replace(" ", "")
        cycle_threshold_value_setting = get_float(target_data, f"{allele} Ct Threshold")
        if cycle_threshold_value_setting is None:
            msg = f"Unable to get cycle threshold value setting for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        cycle_threshold_result = target_data.get(f"{allele} Ct")
        if cycle_threshold_result is None:
            msg = "Unable to get cycle threshold result"
            raise AllotropeConversionError(msg)

        return Result(
            cycle_threshold_value_setting=cycle_threshold_value_setting,
            cycle_threshold_result=float_or_none(cycle_threshold_result),
            automatic_cycle_threshold_enabled_setting=get_bool(
                target_data, f"{allele} Automatic Ct Threshold"
            ),
            automatic_baseline_determination_enabled_setting=get_bool(
                target_data, f"{allele} Automatic Baseline"
            ),
            normalized_reporter_result=get_float(target_data, "Rn"),
            baseline_corrected_reporter_result=get_float(
                target_data, f"{allele} Delta Rn"
            ),
            genotyping_determination_result=get_str(target_data, "Call"),
            genotyping_determination_method_setting=get_float(
                target_data, "Threshold Value"
            ),
            quantity=get_float(target_data, "Quantity"),
            quantity_mean=get_float(target_data, "Quantity Mean"),
            quantity_sd=get_float(target_data, "Quantity SD"),
            ct_mean=get_float(target_data, "Ct Mean"),
            ct_sd=get_float(target_data, "Ct SD"),
            delta_ct_mean=get_float(target_data, "Delta Ct Mean"),
            delta_ct_se=get_float(target_data, "Delta Ct SE"),
            delta_delta_ct=get_float(target_data, "Delta Delta Ct"),
            rq=get_float(target_data, "RQ"),
            rq_min=get_float(target_data, "RQ Min"),
            rq_max=get_float(target_data, "RQ Max"),
            rn_mean=get_float(target_data, "Rn Mean"),
            rn_sd=get_float(target_data, "Rn SD"),
            y_intercept=get_float(target_data, "Y-Intercept"),
            r_squared=get_float(target_data, "R(superscript 2)"),
            slope=get_float(target_data, "Slope"),
            efficiency=get_float(target_data, "Efficiency"),
        )

    @staticmethod
    def filter_target_data(data: pd.DataFrame, well_item: WellItem) -> pd.Series:
        well_data = data[data["Well"] == well_item.identifier]
        if well_data.empty:
            msg = f"Unable to get result data for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        snp_assay_name, _ = well_item.target_dna_description.split("-")
        target_data = well_data[well_data["SNP Assay Name"] == snp_assay_name]
        if target_data.empty:
            msg = f"Unable to get result data for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        n_rows, _ = target_data.shape
        if n_rows != 1:
            msg = f"Unexpected number of results associated to well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        return df_to_series(target_data)


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
            msg = "Unable to find Results section in input file"
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
        well_data = data[data["Well"] == well.identifier]
        if well_data.empty:
            msg = f"Unable to get melt curve raw data for well {well.identifier}"
            raise AllotropeConversionError(msg)

        return well_data

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
                    multi_data, well
                )

            if melt_data is not None:
                well.melt_curve_raw_data = MeltCurveRawDataBuilder.build(
                    melt_data, well
                )

            for well_item in well.items.values():
                well_item.amplification_data = AmplificationData.create(
                    amp_data, well_item
                )
                well_item.result = ResultsBuilder.build(
                    results_data, well_item, header.experiment_type
                )

            if an_well_item := well.get_an_well_item():
                well.calculated_document = build_quantity(an_well_item)

        endogenous_control = get_str(results_metadata, "Endogenous Control") or ""
        reference_sample = get_str(results_metadata, "Reference Sample") or ""

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

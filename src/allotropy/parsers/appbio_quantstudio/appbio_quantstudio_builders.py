from io import StringIO
from typing import Any, Optional
import uuid

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


def get_int(data: pd.Series, key: str) -> Optional[int]:
    try:
        value = data.get(key)
        return None if value is None else int(value)  # type: ignore[arg-type]
    except Exception as e:
        msg = f"Unable to convert {key} to integer value"
        raise AllotropeConversionError(msg) from e


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


class HeaderBuilder:
    @staticmethod
    def build(reader: LinesReader) -> Header:
        data = HeaderBuilder.get_data(reader)

        device_identifier = get_str(data, "Instrument Name")
        if device_identifier is None:
            msg = "Unable to get device identifier"
            raise AllotropeConversionError(msg)

        model_number = get_str(data, "Instrument Type")
        if model_number is None:
            msg = "Unable to get model number"
            raise AllotropeConversionError(msg)

        device_serial_number = get_str(data, "Instrument Serial Number")
        if device_serial_number is None:
            msg = "Unable to get device serial number"
            raise AllotropeConversionError(msg)

        measurement_method_identifier = get_str(data, "Quantification Cycle Method")
        if measurement_method_identifier is None:
            msg = "Unable to get measurement method identifier"
            raise AllotropeConversionError(msg)

        pcr_detection_chemistry = get_str(data, "Chemistry")
        if pcr_detection_chemistry is None:
            msg = "Unable to get PCR detection chemistry"
            raise AllotropeConversionError(msg)

        return Header(
            measurement_time=HeaderBuilder.get_measurement_time(data),
            plate_well_count=HeaderBuilder.get_plate_well_count(data),
            experiment_type=HeaderBuilder.get_experiment_type(data),
            device_identifier=device_identifier,
            model_number=model_number,
            device_serial_number=device_serial_number,
            measurement_method_identifier=measurement_method_identifier,
            pcr_detection_chemistry=pcr_detection_chemistry,
            passive_reference_dye_setting=get_str(data, "Passive Reference"),
            barcode=get_str(data, "Experiment Barcode"),
            analyst=get_str(data, "Experiment User Name"),
            experimental_data_identifier=get_str(data, "Experiment Name"),
        )

    @staticmethod
    def get_experiment_type(data: pd.Series) -> ExperimentType:
        experiments_type_options = {
            "Standard Curve": ExperimentType.standard_curve_qPCR_experiment,
            "Relative Standard Curve": ExperimentType.relative_standard_curve_qPCR_experiment,
            "Comparative Cт (ΔΔCт)": ExperimentType.comparative_CT_qPCR_experiment,
            "Melt Curve": ExperimentType.melt_curve_qPCR_experiment,
            "Genotyping": ExperimentType.genotyping_qPCR_experiment,
            "Presence/Absence": ExperimentType.presence_absence_qPCR_experiment,
        }

        experiments_type = experiments_type_options.get(data.get("Experiment Type"))  # type: ignore[arg-type]
        if experiments_type is None:
            msg = "Unable to get valid experiment type"
            raise AllotropeConversionError(msg)
        return experiments_type

    @staticmethod
    def get_data(reader: LinesReader) -> pd.Series:
        lines = [line.replace("*", "", 1) for line in reader.pop_until(r"^\[.+\]")]
        csv_stream = StringIO("\n".join(lines))
        raw_data = pd.read_csv(
            csv_stream, header=None, sep="=", names=["index", "values"]
        )
        data = pd.Series(raw_data["values"].values, index=raw_data["index"])
        data.index = data.index.str.strip()
        return data.str.strip().replace("NA", None)

    @staticmethod
    def get_measurement_time(data: pd.Series) -> str:
        return str(data.get("Experiment Run End Time"))

    @staticmethod
    def get_plate_well_count(data: pd.Series) -> int:
        block_type = get_str(data, "Block Type", default="")

        if block_type is None:
            msg = "Unable to get plate well count"
            raise AllotropeConversionError(msg)

        if "96" in block_type:
            return 96
        elif "384" in block_type:
            return 384

        msg = "Unable to interpret plate well count"
        raise AllotropeConversionError(msg)


class GenericWellBuilder:
    @staticmethod
    def build(data: pd.DataFrame) -> WellList:
        return WellList(
            [
                Well(
                    identifier=identifier,  # type: ignore[arg-type]
                    items={
                        item_data["Target Name"]: GenericWellBuilder.build_well_item(
                            item_data
                        )
                        for _, item_data in well_data.iterrows()
                    },
                )
                for identifier, well_data in data.groupby("Well")
            ]
        )

    @staticmethod
    def build_well_item(data: pd.Series) -> WellItem:
        identifier = get_int(data, "Well")
        if identifier is None:
            msg = "Unable to get well identifier"
            raise AllotropeConversionError(msg)

        target_dna_description = get_str(data, "Target Name")
        if target_dna_description is None:
            msg = f"Unable to get target dna description for well {identifier}"
            raise AllotropeConversionError(msg)

        sample_identifier = get_str(data, "Sample Name")
        if sample_identifier is None:
            msg = f"Unable to get sample identifier for well {identifier}"
            raise AllotropeConversionError(msg)

        return WellItem(
            uuid=str(uuid.uuid4()),
            identifier=identifier,
            target_dna_description=target_dna_description,
            sample_identifier=sample_identifier,
            reporter_dye_setting=get_str(data, "Reporter"),
            position=get_str(data, "Well Position", default="UNDEFINED"),
            well_location_identifier=get_str(data, "Well Position"),
            quencher_dye_setting=get_str(data, "Quencher"),
            sample_role_type=get_str(data, "Task"),
        )


class GenotypingWellBuilder:
    @staticmethod
    def build(data: pd.DataFrame) -> WellList:
        return WellList(
            [
                Well(
                    identifier=well_id,  # type: ignore[arg-type]
                    items={
                        well_item.target_dna_description: well_item
                        for well_item in GenotypingWellBuilder.build_well_items(
                            well_data
                        )
                    },
                )
                for well_id, well_data in data.iterrows()
            ]
        )

    @staticmethod
    def build_well_items(data: pd.Series) -> list[WellItem]:
        identifier = get_int(data, "Well")
        if identifier is None:
            msg = "Unable to get well identifier"
            raise AllotropeConversionError(msg)

        snp_name = get_str(data, "SNP Assay Name")
        if snp_name is None:
            msg = f"Unable to get snp name for well {identifier}"
            raise AllotropeConversionError(msg)

        allele1 = get_str(data, "Allele1 Name")
        if allele1 is None:
            msg = f"Unable to get allele 1 for well {identifier}"
            raise AllotropeConversionError(msg)

        allele2 = get_str(data, "Allele2 Name")
        if allele2 is None:
            msg = f"Unable to get allele 2 for well {identifier}"
            raise AllotropeConversionError(msg)

        sample_identifier = get_str(data, "Sample Name")
        if sample_identifier is None:
            msg = "Unable to get sample identifier"
            raise AllotropeConversionError(msg)

        return [
            WellItem(
                uuid=str(uuid.uuid4()),
                identifier=identifier,
                target_dna_description=f"{snp_name}-{allele}",
                sample_identifier=sample_identifier,
                reporter_dye_setting=get_str(data, "Reporter"),
                position=get_str(data, "Well Position", default="UNDEFINED"),
                well_location_identifier=get_str(data, "Well Position"),
                quencher_dye_setting=get_str(data, "Quencher"),
                sample_role_type=get_str(data, "Task"),
            )
            for allele in [allele1, allele2]
        ]


class WellBuilder:
    @staticmethod
    def build(reader: LinesReader, experiment_type: ExperimentType) -> WellList:
        raw_data = WellBuilder.get_data(reader)
        data = raw_data[raw_data["Sample Name"].notnull()]
        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return GenotypingWellBuilder.build(data)
        return GenericWellBuilder.build(data)

    @staticmethod
    def get_data(reader: LinesReader) -> pd.DataFrame:
        if reader.drop_until(r"^\[Sample Setup\]") is None:
            msg = "Unable to find Sample Setup section in input file"
            raise AllotropeConversionError(msg)

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t").replace(np.nan, None)


class RawDataBuilder:
    @staticmethod
    def build(reader: LinesReader) -> Optional[RawData]:
        if not reader.match(r"^\[Raw Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        return RawData(lines)


class AmplificationDataBuilder:
    @staticmethod
    def build(
        amplification_data: pd.DataFrame, well_item: WellItem
    ) -> AmplificationData:
        target_data = AmplificationDataBuilder.filter_target_data(
            amplification_data, well_item
        )
        return AmplificationData(
            total_cycle_number_setting=float(target_data["Cycle"].max()),
            cycle=target_data["Cycle"].tolist(),
            rn=target_data["Rn"].tolist(),
            delta_rn=target_data["Delta Rn"].tolist(),
        )

    @staticmethod
    def filter_target_data(
        amplification_data: pd.DataFrame, well_item: WellItem
    ) -> pd.DataFrame:
        well_data = amplification_data[
            amplification_data["Well"] == well_item.identifier
        ]
        if well_data.empty:
            msg = f"Unable to get amplification data for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        target_data = well_data[
            well_data["Target Name"] == well_item.target_dna_description
        ]
        if target_data.empty:
            msg = f"Unable to get amplification data for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        return target_data

    @staticmethod
    def get_data(reader: LinesReader) -> pd.DataFrame:
        if reader.drop_until(r"^\[Amplification Data\]") is None:
            msg = "Unable to find Amplification Data section in input file"
            raise AllotropeConversionError(msg)

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t", thousands=r",")


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
        header = HeaderBuilder.build(reader)
        wells = WellBuilder.build(reader, header.experiment_type)
        raw_data = RawDataBuilder.build(reader)

        amp_data = AmplificationDataBuilder.get_data(reader)
        multi_data = MulticomponentDataBuilder.get_data(reader)
        results_data, results_metadata = ResultsBuilder.get_data(reader)
        melt_data = MeltCurveRawDataBuilder.get_data(reader)
        for well in wells:
            if multi_data is not None:
                well.add_multicomponent_data(
                    MulticomponentDataBuilder.build(multi_data, well)
                )
            if melt_data is not None:
                well.add_melt_curve_raw_data(
                    MeltCurveRawDataBuilder.build(melt_data, well)
                )
            for well_item in well.items.values():
                well_item.add_amplification_data(
                    AmplificationDataBuilder.build(amp_data, well_item)
                )
                well_item.add_result(
                    ResultsBuilder.build(
                        results_data, well_item, header.experiment_type
                    )
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

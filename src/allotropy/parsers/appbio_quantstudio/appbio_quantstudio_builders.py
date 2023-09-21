from io import StringIO
from typing import Any, Optional

import numpy as np
import pandas as pd

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import (
    ExperimentType,
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
)
from allotropy.parsers.lines_reader import LinesReader


def df_to_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(df.iloc[0], index=df.columns)


def float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


class HeaderBuilder:
    @staticmethod
    def build(reader: LinesReader) -> Header:
        data = HeaderBuilder.get_data(reader)

        device_identifier = data.get("Instrument Name")
        if device_identifier is None:
            msg = "Unable to get device identifier"
            raise AllotropeConversionError(msg)

        model_number = data.get("Instrument Type")
        if model_number is None:
            msg = "Unable to get model number"
            raise AllotropeConversionError(msg)

        device_serial_number = data.get("Instrument Serial Number")
        if device_serial_number is None:
            msg = "Unable to get device serial number"
            raise AllotropeConversionError(msg)

        measurement_method_identifier = data.get("Quantification Cycle Method")
        if measurement_method_identifier is None:
            msg = "Unable to get measurement method identifier"
            raise AllotropeConversionError(msg)

        qpcr_detection_chemistry = data.get("Chemistry")
        if qpcr_detection_chemistry is None:
            msg = "Unable to get qpcr detection chemistry"
            raise AllotropeConversionError(msg)

        return Header(
            measurement_time=HeaderBuilder.get_measurement_time(data),
            plate_well_count=HeaderBuilder.get_plate_well_count(data),
            experiment_type=HeaderBuilder.get_experiment_type(data),
            device_identifier=device_identifier,  # type: ignore[arg-type]
            model_number=model_number,  # type: ignore[arg-type]
            device_serial_number=device_serial_number,  # type: ignore[arg-type]
            measurement_method_identifier=measurement_method_identifier,  # type: ignore[arg-type]
            qpcr_detection_chemistry=qpcr_detection_chemistry,  # type: ignore[arg-type]
            passive_reference_dye_setting=data.get("Passive Reference"),  # type: ignore[arg-type]
            barcode=data.get("Experiment Barcode"),  # type: ignore[arg-type]
            analyst=data.get("Experiment User Name"),  # type: ignore[arg-type]
            experimental_data_identifier=data.get("Experiment Name"),  # type: ignore[arg-type]
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
        block_type = data.get("Block Type", "")

        if block_type.startswith("96"):  # type: ignore[union-attr]
            return 96
        elif block_type.startswith("384"):  # type: ignore[union-attr]
            return 384

        msg = "Unable to get plate well count"
        raise AllotropeConversionError(msg)


class GenericWellBuilder:
    @staticmethod
    def build(data: pd.DataFrame) -> list[Well]:
        return [
            Well(
                identifier=identifier,  # type: ignore[arg-type]
                items={
                    well_item_data["Target Name"]: GenericWellBuilder.build_well_item(
                        well_item_data
                    )
                    for _, well_item_data in well_data.iterrows()
                },
            )
            for identifier, well_data in data.groupby("Well")
        ]

    @staticmethod
    def build_well_item(data: pd.Series) -> WellItem:
        identifier = data.get("Well")
        if identifier is None:
            msg = "Unable to get well identifier"
            raise AllotropeConversionError(msg)

        target_dna_description = data.get("Target Name")
        if target_dna_description is None:
            msg = f"Unable to get target dna description for well {identifier}"
            raise AllotropeConversionError(msg)

        sample_identifier = data.get("Sample Name")
        if sample_identifier is None:
            msg = f"Unable to get sample identifier for well {identifier}"
            raise AllotropeConversionError(msg)

        return WellItem(
            identifier=identifier,  # type: ignore[arg-type]
            target_dna_description=target_dna_description,  # type: ignore[arg-type]
            sample_identifier=sample_identifier,  # type: ignore[arg-type]
            reporter_dye_setting=data.get("Reporter"),  # type: ignore[arg-type]
            position=data.get("Well Position", "UNDEFINED"),  # type: ignore[arg-type]
            well_location_identifier=data.get("Well Position"),  # type: ignore[arg-type]
            quencher_dye_setting=data.get("Quencher"),  # type: ignore[arg-type]
            sample_role_type=data.get("Task"),  # type: ignore[arg-type]
        )


class GenotypingWellBuilder:
    @staticmethod
    def build(data: pd.DataFrame) -> list[Well]:
        return [
            Well(
                identifier=well_id,  # type: ignore[arg-type]
                items={
                    well_item.target_dna_description: well_item
                    for well_item in GenotypingWellBuilder.build_well_items(well_data)
                },
            )
            for well_id, well_data in data.iterrows()
        ]

    @staticmethod
    def build_well_items(data: pd.Series) -> list[WellItem]:
        identifier = data.get("Well")
        if identifier is None:
            msg = "Unable to get well identifier"
            raise AllotropeConversionError(msg)

        snp_name = data.get("SNP Assay Name")
        if snp_name is None:
            msg = f"Unable to get snp name for well {identifier}"
            raise AllotropeConversionError(msg)

        allele1 = data.get("Allele1 Name")
        if allele1 is None:
            msg = f"Unable to get allele 1 for well {identifier}"
            raise AllotropeConversionError(msg)

        allele2 = data.get("Allele2 Name")
        if allele2 is None:
            msg = f"Unable to get allele 2 for well {identifier}"
            raise AllotropeConversionError(msg)

        sample_identifier = data.get("Sample Name")
        if sample_identifier is None:
            msg = "Unable to get sample identifier"
            raise AllotropeConversionError(msg)

        return [
            WellItem(
                identifier=identifier,  # type: ignore[arg-type]
                target_dna_description=f"{snp_name}-{allele}",
                sample_identifier=sample_identifier,  # type: ignore[arg-type]
                reporter_dye_setting=data.get("Reporter"),  # type: ignore[arg-type]
                position=data.get("Well Position", "UNDEFINED"),  # type: ignore[arg-type]
                well_location_identifier=data.get("Well Position"),  # type: ignore[arg-type]
                quencher_dye_setting=data.get("Quencher"),  # type: ignore[arg-type]
                sample_role_type=data.get("Task"),  # type: ignore[arg-type]
            )
            for allele in [allele1, allele2]
        ]


class WellBuilder:
    @staticmethod
    def build(reader: LinesReader, experiment_type: ExperimentType) -> list[Well]:
        raw_data = WellBuilder.get_data(reader)
        data = raw_data[raw_data["Sample Name"].notnull()]
        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return GenotypingWellBuilder.build(data)
        return GenericWellBuilder.build(data)

    @staticmethod
    def get_data(reader: LinesReader) -> pd.DataFrame:
        if not reader.match(r"^\[Sample Setup\]"):
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
        if not reader.match(r"^\[Amplification Data\]"):
            msg = "Unable to find Amplification Data section in input file"
            raise AllotropeConversionError(msg)

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t")


class MulticomponentDataBuilder:
    @staticmethod
    def build(data: pd.DataFrame, well: Well) -> MulticomponentData:
        well_data = MulticomponentDataBuilder.filter_well_data(data, well)
        return MulticomponentData(
            cycle=well_data["Cycle"].tolist(),
            columns={
                name: well_data[name].str.replace(",", "").astype(float).tolist()  # type: ignore[misc]
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
        return pd.read_csv(csv_stream, sep="\t")


class GenericResultsBuilder:
    @staticmethod
    def build(data: pd.DataFrame, well_item: WellItem) -> Result:
        target_data = GenericResultsBuilder.filter_target_data(data, well_item)
        cycle_threshold_value_setting = target_data.get("Ct Threshold")
        if cycle_threshold_value_setting is None:
            msg = "Unable to get cycle threshold value setting"
            raise AllotropeConversionError(msg)

        cycle_threshold_result = target_data.get("CT")
        if cycle_threshold_result is None:
            msg = "Unable to get cycle threshold result"
            raise AllotropeConversionError(msg)

        return Result(
            cycle_threshold_value_setting=cycle_threshold_value_setting,  # type: ignore[arg-type]
            cycle_threshold_result=float_or_none(cycle_threshold_result),
            automatic_cycle_threshold_enabled_setting=target_data.get("Automatic Ct Threshold"),  # type: ignore[arg-type]
            automatic_baseline_determination_enabled_setting=target_data.get("Automatic Baseline"),  # type: ignore[arg-type]
            normalized_reporter_result=target_data.get("Rn"),  # type: ignore[arg-type]
            baseline_corrected_reporter_result=target_data.get("Delta Rn"),  # type: ignore[arg-type]
            genotyping_determination_result=target_data.get("Call"),  # type: ignore[arg-type]
            genotyping_determination_method_setting=target_data.get("Threshold Value"),  # type: ignore[arg-type]
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
        cycle_threshold_value_setting = target_data.get(f"{allele} Ct Threshold")
        if cycle_threshold_value_setting is None:
            msg = f"Unable to get cycle threshold value setting for well {well_item.identifier}"
            raise AllotropeConversionError(msg)

        cycle_threshold_result = target_data.get(f"{allele} Ct")
        if cycle_threshold_result is None:
            msg = "Unable to get cycle threshold result"
            raise AllotropeConversionError(msg)

        return Result(
            cycle_threshold_value_setting=cycle_threshold_value_setting,  # type: ignore[arg-type]
            cycle_threshold_result=float_or_none(cycle_threshold_result),
            automatic_cycle_threshold_enabled_setting=target_data.get(f"{allele} Automatic Ct Threshold"),  # type: ignore[arg-type]
            automatic_baseline_determination_enabled_setting=target_data.get(f"{allele} Automatic Baseline"),  # type: ignore[arg-type]
            normalized_reporter_result=target_data.get("Rn"),  # type: ignore[arg-type]
            baseline_corrected_reporter_result=target_data.get(f"{allele} Delta Rn"),  # type: ignore[arg-type]
            genotyping_determination_result=target_data.get("Call"),  # type: ignore[arg-type]
            genotyping_determination_method_setting=target_data.get("Threshold Value"),  # type: ignore[arg-type]
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
    def get_data(reader: LinesReader) -> pd.DataFrame:
        if not reader.match(r"^\[Results\]"):
            msg = "Unable to find Results section in input file"
            raise AllotropeConversionError(msg)

        reader.pop()  # remove title
        lines = list(reader.pop_until_empty())
        reader.drop_until(r"^\[Melt Curve Raw Data\]")
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t")


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
        return pd.read_csv(csv_stream, sep="\t")


class DataBuilder:
    @staticmethod
    def build(reader: LinesReader) -> Data:
        header = HeaderBuilder.build(reader)
        wells = WellBuilder.build(reader, header.experiment_type)
        raw_data = RawDataBuilder.build(reader)

        amp_data = AmplificationDataBuilder.get_data(reader)
        multi_data = MulticomponentDataBuilder.get_data(reader)
        results_data = ResultsBuilder.get_data(reader)
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
        return Data(
            header,
            wells,
            raw_data,
        )

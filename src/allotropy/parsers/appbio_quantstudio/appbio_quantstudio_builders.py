# mypy: disallow_any_generics = False

from io import StringIO
import re
from typing import Optional
import uuid

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
    try_int,
    try_int_from_series,
    try_str_from_series,
    try_str_from_series_or_none,
)


class HeaderBuilder:
    @staticmethod
    def build(reader: LinesReader) -> Header:
        data = HeaderBuilder.get_data(reader)

        return Header(
            measurement_time=HeaderBuilder.get_measurement_time(data),
            plate_well_count=HeaderBuilder.get_plate_well_count(data),
            experiment_type=HeaderBuilder.get_experiment_type(data),
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
            pcr_detection_chemistry=try_str_from_series(data, "Chemistry"),
            passive_reference_dye_setting=try_str_from_series_or_none(
                data, "Passive Reference"
            ),
            barcode=try_str_from_series_or_none(data, "Experiment Barcode"),
            analyst=try_str_from_series_or_none(data, "Experiment User Name"),
            experimental_data_identifier=try_str_from_series_or_none(
                data, "Experiment Name"
            ),
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

        return assert_not_none(
            experiments_type_options.get(
                try_str_from_series(data, "Experiment Type"),
            ),
            msg="Unable to find valid experiment type",
        )

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
        block_type = try_str_from_series(data, "Block Type")
        return try_int(
            assert_not_none(
                re.match("(96)|(384)", block_type),
                msg="Unable to interpret plate well count",
            ).group(),
            "plate well count",
        )


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
        identifier = try_int_from_series(data, "Well")

        target_dna_description = try_str_from_series(
            data,
            "Target Name",
            msg=f"Unable to find target dna description for well {identifier}",
        )

        sample_identifier = try_str_from_series(
            data,
            "Sample Name",
            msg=f"Unable to find sample identifier for well {identifier}",
        )

        return WellItem(
            uuid=str(uuid.uuid4()),
            identifier=identifier,
            target_dna_description=target_dna_description,
            sample_identifier=sample_identifier,
            reporter_dye_setting=try_str_from_series_or_none(data, "Reporter"),
            position=try_str_from_series_or_none(
                data, "Well Position", default="UNDEFINED"
            ),
            well_location_identifier=try_str_from_series_or_none(data, "Well Position"),
            quencher_dye_setting=try_str_from_series_or_none(data, "Quencher"),
            sample_role_type=try_str_from_series_or_none(data, "Task"),
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
    def build_well_items(data: pd.Series) -> tuple[WellItem, WellItem]:
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
                position=try_str_from_series_or_none(
                    data, "Well Position", default="UNDEFINED"
                ),
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
                position=try_str_from_series_or_none(
                    data, "Well Position", default="UNDEFINED"
                ),
                well_location_identifier=try_str_from_series_or_none(
                    data, "Well Position"
                ),
                quencher_dye_setting=try_str_from_series_or_none(data, "Quencher"),
                sample_role_type=try_str_from_series_or_none(data, "Task"),
            ),
        )


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
            msg = "Unable to find 'Sample Setup' section in file."
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
        well_data = assert_not_empty_df(
            amplification_data[amplification_data["Well"] == well_item.identifier],
            msg=f"Unable to find amplification data for well {well_item.identifier}.",
        )

        return assert_not_empty_df(
            well_data[well_data["Target Name"] == well_item.target_dna_description],
            msg=f"Unable to find amplification data for well {well_item.identifier}.",
        )

    @staticmethod
    def get_data(reader: LinesReader) -> pd.DataFrame:
        if reader.drop_until(r"^\[Amplification Data\]") is None:
            msg = "Unable to find 'Amplification Data' section in file."
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

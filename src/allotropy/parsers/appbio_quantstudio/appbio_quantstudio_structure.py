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
from io import StringIO
import re
from typing import Optional
import uuid

import numpy as np
import pandas as pd

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio.calculated_document import CalculatedDocument
from allotropy.parsers.appbio_quantstudio.referenceable import Referenceable
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import (
    assert_int,
    assert_not_none,
    try_float,
    try_int,
)


def df_to_series(df: pd.DataFrame, msg: str) -> pd.Series:
    n_rows, _ = df.shape
    if n_rows == 1:
        return pd.Series(df.iloc[0], index=df.columns)
    raise AllotropeConversionError(msg)


def assert_not_empty(df: pd.DataFrame, msg: str) -> pd.DataFrame:
    if df.empty:
        raise AllotropeConversionError(msg)
    return df


def get_str(data: pd.Series, key: str, default: Optional[str] = None) -> Optional[str]:
    value = data.get(key, default)
    return None if value is None else str(value)


def assert_get_str(series: pd.Series, key: str, msg: Optional[str] = None) -> str:
    return assert_not_none(get_str(series, key), key, msg)


def get_int(data: pd.Series, key: str) -> Optional[int]:
    try:
        value = data.get(key)
        return try_int(str(value))
    except Exception as e:
        msg = f"Unable to convert {key} to integer value"
        raise AllotropeConversionError(msg) from e


def assert_get_int(data: pd.Series, key: str, msg: Optional[str] = None) -> int:
    return assert_not_none(get_int(data, key), key, msg)


def get_float(data: pd.Series, key: str) -> Optional[float]:
    try:
        value = data.get(key)
        return try_float(str(value))
    except Exception as e:
        msg = f"Unable to convert {key} to float value"
        raise AllotropeConversionError(msg) from e


def assert_get_float(data: pd.Series, key: str, msg: Optional[str] = None) -> float:
    return assert_not_none(get_float(data, key), key, msg)


def get_bool(data: pd.Series, key: str) -> Optional[bool]:
    try:
        value = data.get(key)
        return None if value is None else bool(value)
    except Exception as e:
        msg = f"Unable to convert {key} to bool value"
        raise AllotropeConversionError(msg) from e


@dataclass
class Header:
    measurement_time: str
    plate_well_count: int
    experiment_type: ExperimentType
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    pcr_detection_chemistry: str
    passive_reference_dye_setting: Optional[str]
    barcode: Optional[str]
    analyst: Optional[str]
    experimental_data_identifier: Optional[str]

    @staticmethod
    def create(reader: LinesReader) -> Header:
        lines = [line.replace("*", "", 1) for line in reader.pop_until(r"^\[.+\]")]
        csv_stream = StringIO("\n".join(lines))
        raw_data = pd.read_csv(
            csv_stream, header=None, sep="=", names=["index", "values"]
        )
        data = pd.Series(raw_data["values"].values, index=raw_data["index"])
        data.index = data.index.str.strip()
        data = data.str.strip().replace("NA", None)

        block_type = assert_get_str(data, "Block Type")
        plate_well_count = assert_not_none(
            try_int(
                assert_not_none(
                    re.match("(96)|(384)", block_type),
                    msg="Unable to interpret plate well count",
                ).group()
            )
        )

        experiments_type_options = {
            "Standard Curve": ExperimentType.standard_curve_qPCR_experiment,
            "Relative Standard Curve": ExperimentType.relative_standard_curve_qPCR_experiment,
            "Comparative Cт (ΔΔCт)": ExperimentType.comparative_CT_qPCR_experiment,
            "Melt Curve": ExperimentType.melt_curve_qPCR_experiment,
            "Genotyping": ExperimentType.genotyping_qPCR_experiment,
            "Presence/Absence": ExperimentType.presence_absence_qPCR_experiment,
        }

        experiments_type = assert_not_none(
            experiments_type_options.get(
                assert_get_str(data, "Experiment Type"),
            ),
            msg="Unable to get valid experiment type",
        )

        return Header(
            measurement_time=assert_get_str(data, "Experiment Run End Time"),
            plate_well_count=plate_well_count,
            experiment_type=experiments_type,
            device_identifier=assert_get_str(data, "Instrument Name"),
            model_number=assert_get_str(data, "Instrument Type"),
            device_serial_number=assert_get_str(data, "Instrument Serial Number"),
            measurement_method_identifier=assert_get_str(
                data, "Quantification Cycle Method"
            ),
            pcr_detection_chemistry=assert_get_str(data, "Chemistry"),
            passive_reference_dye_setting=get_str(data, "Passive Reference"),
            barcode=get_str(data, "Experiment Barcode"),
            analyst=get_str(data, "Experiment User Name"),
            experimental_data_identifier=get_str(data, "Experiment Name"),
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

    @property
    def amplification_data(self) -> AmplificationData:
        return assert_not_none(
            self._amplification_data,
            f"Unable to find amplification data for well {self.identifier}",
        )

    @amplification_data.setter
    def amplification_data(self, amplification_data: AmplificationData) -> None:
        self._amplification_data = amplification_data

    @property
    def result(self) -> Result:
        return assert_not_none(
            self._result,
            f"Unablt to find result data for well {self.identifier}",
        )

    @result.setter
    def result(self, result: Result) -> None:
        self._result = result

    @staticmethod
    def create_genotyping(data: pd.Series) -> list[WellItem]:
        identifier = assert_get_int(data, "Well")
        snp_name = assert_get_str(
            data,
            "SNP Assay Name",
            msg=f"Unable to get snp name for well {identifier}",
        )

        allele1 = assert_get_str(
            data,
            "Allele1 Name",
            msg=f"Unable to get allele 1 for well {identifier}",
        )
        allele2 = assert_get_str(
            data,
            "Allele2 Name",
            msg=f"Unable to get allele 2 for well {identifier}",
        )

        return [
            WellItem(
                uuid=str(uuid.uuid4()),
                identifier=identifier,
                target_dna_description=f"{snp_name}-{allele}",
                sample_identifier=assert_get_str(
                    data,
                    "Sample Name",
                    msg=f"Unable to get sample identifier for well {identifier}",
                ),
                reporter_dye_setting=get_str(data, "Reporter"),
                position=get_str(data, "Well Position", default="UNDEFINED"),
                well_location_identifier=get_str(data, "Well Position"),
                quencher_dye_setting=get_str(data, "Quencher"),
                sample_role_type=get_str(data, "Task"),
            )
            for allele in [allele1, allele2]
        ]

    @staticmethod
    def create_generic(data: pd.Series) -> WellItem:
        identifier = assert_get_int(data, "Well")
        target_dna_description = assert_get_str(
            data,
            "Target Name",
            msg=f"Unable to get target dna description for well {identifier}",
        )
        sample_identifier = assert_get_str(
            data,
            "Sample Name",
            msg=f"Unable to get sample identifier for well {identifier}",
        )

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


@dataclass
class Well:
    identifier: int
    items: dict[str, WellItem]
    _multicomponent_data: Optional[MulticomponentData] = None
    _melt_curve_raw_data: Optional[MeltCurveRawData] = None
    _calculated_document: Optional[CalculatedDocument] = None

    def get_well_item(self, target: str) -> WellItem:
        return assert_not_none(
            self.items.get(target),
            msg=f"Unable to find target dna {target} for well {self.identifier}",
        )

    def get_an_well_item(self) -> Optional[WellItem]:
        if not self.items:
            return None
        target, *_ = self.items.keys()
        return self.items[target]

    @property
    def multicomponent_data(self) -> Optional[MulticomponentData]:
        return self._multicomponent_data

    @multicomponent_data.setter
    def multicomponent_data(self, multicomponent_data: MulticomponentData) -> None:
        self._multicomponent_data = multicomponent_data

    @property
    def melt_curve_raw_data(self) -> Optional[MeltCurveRawData]:
        return self._melt_curve_raw_data

    @melt_curve_raw_data.setter
    def melt_curve_raw_data(self, melt_curve_raw_data: MeltCurveRawData) -> None:
        self._melt_curve_raw_data = melt_curve_raw_data

    @property
    def calculated_document(self) -> Optional[CalculatedDocument]:
        return self._calculated_document

    @calculated_document.setter
    def calculated_document(self, calculated_document: CalculatedDocument) -> None:
        self._calculated_document = calculated_document

    @staticmethod
    def create_genotyping(well_id: int, well_data: pd.Series) -> Well:
        return Well(
            identifier=well_id,
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
                item_data["Target Name"]: WellItem.create_generic(item_data)
                for _, item_data in well_data.iterrows()
            },
        )


@dataclass
class WellList:
    wells: list[Well]

    def iter_well_items(self) -> Iterator[WellItem]:
        for well in self.wells:
            yield from well.items.values()

    def __iter__(self) -> Iterator[Well]:
        return iter(self.wells)

    @staticmethod
    def create(reader: LinesReader, experiment_type: ExperimentType) -> WellList:
        assert_not_none(
            reader.drop_until(r"^\[Sample Setup\]"),
            "Unable to find Sample Setup section in input file",
        )

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        raw_data = pd.read_csv(csv_stream, sep="\t").replace(np.nan, None)
        data = raw_data[raw_data["Sample Name"].notnull()]

        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return WellList(
                [
                    Well.create_genotyping(assert_int(str(identifier)), well_data)
                    for identifier, well_data in data.iterrows()
                ]
            )

        return WellList(
            [
                Well.create_generic(assert_int(str(identifier)), well_data)
                for identifier, well_data in data.groupby("Well")
            ]
        )


@dataclass
class RawData:
    lines: list[str]

    @staticmethod
    def create(reader: LinesReader) -> Optional[RawData]:
        if not reader.match(r"^\[Raw Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        return RawData(lines)


@dataclass
class AmplificationData:
    total_cycle_number_setting: float
    cycle: list[float]
    rn: list[Optional[float]]
    delta_rn: list[Optional[float]]

    @staticmethod
    def get_data(reader: LinesReader) -> pd.DataFrame:
        if reader.drop_until(r"^\[Amplification Data\]") is None:
            msg = "Unable to find Amplification Data section in input file"
            raise AllotropeConversionError(msg)

        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t", thousands=r",")

    @staticmethod
    def create(
        amplification_data: pd.DataFrame, well_item: WellItem
    ) -> AmplificationData:
        well_data = assert_not_empty(
            amplification_data[amplification_data["Well"] == well_item.identifier],
            msg=f"Unable to get amplification data for well {well_item.identifier}",
        )

        target_data = assert_not_empty(
            well_data[well_data["Target Name"] == well_item.target_dna_description],
            msg=f"Unable to get amplification data for well {well_item.identifier}",
        )

        return AmplificationData(
            total_cycle_number_setting=float(target_data["Cycle"].max()),
            cycle=target_data["Cycle"].tolist(),
            rn=target_data["Rn"].tolist(),
            delta_rn=target_data["Delta Rn"].tolist(),
        )


@dataclass
class MulticomponentData:
    cycle: list[float]
    columns: dict[str, list[Optional[float]]]

    def get_column(self, name: str) -> list[Optional[float]]:
        return assert_not_none(
            self.columns.get(name),
            msg=f"Unable to obtain {name} from multicomponent data",
        )

    @staticmethod
    def create(data: pd.DataFrame, well: Well) -> MulticomponentData:
        well_data = assert_not_empty(
            data[data["Well"] == well.identifier],
            msg=f"Unable to find multi component data for well {well.identifier}",
        )

        return MulticomponentData(
            cycle=well_data["Cycle"].tolist(),
            columns={
                name: well_data[name].tolist()  # type: ignore[misc]
                for name in well_data
                if name not in ["Well", "Cycle", "Well Position"]
            },
        )

    @staticmethod
    def get_data(reader: LinesReader) -> Optional[pd.DataFrame]:
        if not reader.match(r"^\[Multicomponent Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until(r"^\[.+\]"))
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t", thousands=r",")


@dataclass
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
    def create_genotyping(data: pd.DataFrame, well_item: WellItem) -> Result:
        well_data = assert_not_empty(
            data[data["Well"] == well_item.identifier],
            msg=f"Unable to get result data for well {well_item.identifier}",
        )

        snp_assay_name, _ = well_item.target_dna_description.split("-")
        target_data = df_to_series(
            assert_not_empty(
                well_data[well_data["SNP Assay Name"] == snp_assay_name],
                msg=f"Unable to get result data for well {well_item.identifier}",
            ),
            msg=f"Unexpected number of results associated to well {well_item.identifier}",
        )

        _, raw_allele = well_item.target_dna_description.split("-")
        allele = raw_allele.replace(" ", "")

        cycle_threshold_result = assert_not_none(
            target_data.get(f"{allele} Ct"),
            msg="Unable to get cycle threshold result",
        )

        return Result(
            cycle_threshold_value_setting=assert_get_float(
                target_data,
                f"{allele} Ct Threshold",
                msg=f"Unable to get cycle threshold value setting for well {well_item.identifier}",
            ),
            cycle_threshold_result=try_float(str(cycle_threshold_result)),
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
    def create_generic(data: pd.DataFrame, well_item: WellItem) -> Result:
        well_data = assert_not_empty(
            data[data["Well"] == well_item.identifier],
            msg=f"Unable to get result data for well {well_item.identifier}",
        )

        target_data = df_to_series(
            assert_not_empty(
                well_data[well_data["Target Name"] == well_item.target_dna_description],
                msg=f"Unable to get result data for well {well_item.identifier}",
            ),
            msg=f"Unexpected number of results associated to well {well_item.identifier}",
        )

        cycle_threshold_result = assert_not_none(
            target_data.get("CT"),
            msg="Unable to get cycle threshold result",
        )

        return Result(
            cycle_threshold_value_setting=assert_get_float(
                target_data,
                "Ct Threshold",
                msg="Unable to get cycle threshold value setting",
            ),
            cycle_threshold_result=try_float(str(cycle_threshold_result)),
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
    def create(
        data: pd.DataFrame, well_item: WellItem, experiment_type: ExperimentType
    ) -> Result:
        if experiment_type == ExperimentType.genotyping_qPCR_experiment:
            return Result.create_genotyping(data, well_item)
        return Result.create_generic(data, well_item)

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


@dataclass
class MeltCurveRawData:
    reading: list[float]
    fluorescence: list[Optional[float]]
    derivative: list[Optional[float]]

    @staticmethod
    def create(data: pd.DataFrame, well: Well) -> MeltCurveRawData:
        well_data = assert_not_empty(
            data[data["Well"] == well.identifier],
            msg=f"Unable to get melt curve raw data for well {well.identifier}",
        )

        return MeltCurveRawData(
            reading=well_data["Reading"].tolist(),
            fluorescence=well_data["Fluorescence"].tolist(),
            derivative=well_data["Derivative"].tolist(),
        )

    @staticmethod
    def get_data(reader: LinesReader) -> Optional[pd.DataFrame]:
        if not reader.match(r"^\[Melt Curve Raw Data\]"):
            return None
        reader.pop()  # remove title
        lines = list(reader.pop_until_empty())
        csv_stream = StringIO("\n".join(lines))
        return pd.read_csv(csv_stream, sep="\t", thousands=r",")


@dataclass
class Data:
    header: Header
    wells: WellList
    raw_data: Optional[RawData]
    endogenous_control: str
    reference_sample: str
    calculated_documents: list[CalculatedDocument]

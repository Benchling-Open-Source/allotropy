from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import Optional
import uuid

import pandas as pd

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
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
            model_number=try_str_from_series(header, "Instrument Type"),
            device_serial_number=try_str_from_series_or_none(
                header, "Instrument Serial Number"
            )
            or "NA",
            measurement_method_identifier=try_str_from_series(
                header, "Quantification Cycle Method"
            ),
            pcr_detection_chemistry=try_str_from_series_or_none(header, "Chemistry"),
            passive_reference_dye_setting=try_str_from_series_or_none(
                header, "Passive Reference"
            ),
            barcode=try_str_from_series_or_none(header, "Barcode"),
            analyst=try_str_from_series_or_none(header, "Operator"),
            experimental_data_identifier=try_str_from_series_or_none(
                header, "Experiment Name"
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
    def create(data: pd.Series[str]) -> WellItem:
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
                item_data["Target"]: WellItem.create(item_data)
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
    def create(contents: DesignQuantstudioContents) -> WellList:
        assert_not_empty_df(
            contents.data["Results"],
            msg="Unable to find 'Results' sheet in file.",
        )

        raw_data = contents.data["Results"]
        data = raw_data[raw_data["Sample"].notnull()]
        return WellList(
            [
                Well.create(
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
    def get_data(contents: DesignQuantstudioContents) -> pd.DataFrame:
        assert_not_empty_df(
            contents.data["Amplification Data"],
            msg="Unable to find 'Amplification Data' sheet in file.",
        )
        return contents.data["Amplification Data"]

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
    def get_data(contents: DesignQuantstudioContents) -> Optional[pd.DataFrame]:
        if "Multicomponent" in contents.data:
            if not contents.data["Multicomponent"].empty:
                return contents.data["Multicomponent"]
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
    def get_data(contents: DesignQuantstudioContents) -> pd.DataFrame:
        return contents.data["Results"]

    @staticmethod
    def create(data: pd.DataFrame, well_item: WellItem) -> Result:
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


@dataclass(frozen=True)
class Data:
    header: Header
    wells: WellList

    @staticmethod
    def create(contents: DesignQuantstudioContents) -> Data:
        header = Header.create(contents.header)
        wells = WellList.create(contents)

        amp_data = AmplificationData.get_data(contents)
        multi_data = MulticomponentData.get_data(contents)
        results_data = Result.get_data(contents)
        for well in wells:
            if multi_data is not None:
                well.multicomponent_data = MulticomponentData.create(
                    multi_data, well, header
                )

            for well_item in well.items.values():
                well_item.amplification_data = AmplificationData.create(
                    amp_data,
                    well_item,
                )

                well_item.result = Result.create(
                    results_data,
                    well_item,
                )

        return Data(
            header,
            wells,
        )

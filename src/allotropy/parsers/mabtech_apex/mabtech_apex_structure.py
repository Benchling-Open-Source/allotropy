from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import InvalidJsonFloat
from allotropy.parsers.mabtech_apex.mabtech_apex_contents import MabtechApexContents
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_from_series_or_nan,
    try_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)

IMAGE_FEATURES = [
    "Spot Forming Units (SFU)",
    "Average Relative Spot Volume (RSV)",
    "Sum of Spot Volume (RSV)",
]


@dataclass(frozen=True)
class PlateInformation:
    unc_path: str | None
    analyst: str | None
    software_version: str | None
    model_number: str
    equipment_serial_number: str | None

    @staticmethod
    def create(contents: MabtechApexContents) -> PlateInformation:
        plateinformation = contents.plate_info
        machine_id = assert_not_none(
            re.match(
                "([A-Z]+[a-z]+) ([0-9]+)",
                try_str_from_series(plateinformation, key="Machine ID:"),
            ),
            msg="Unable to interpret Machine ID",
        )

        return PlateInformation(
            unc_path=try_str_from_series_or_none(plateinformation, key="Path:"),
            analyst=try_str_from_series_or_none(plateinformation, key="Saved By:"),
            software_version=try_str_from_series_or_none(
                plateinformation, key="Software Version:"
            ),
            model_number=machine_id.group(1),
            equipment_serial_number=machine_id.group(2),
        )


@dataclass(frozen=True)
class Well:
    measurement_time: str
    sample_identifier: str
    location_identifier: str
    well_plate_identifier: str | None
    exposure_duration_setting: float | None
    illumination_setting: float | None
    image_features: list[dict[str, float | InvalidJsonFloat]]

    @staticmethod
    def create(plate_data: pd.Series[str]) -> Well | None:
        # if Read Date is not present in file, return None, no measurement for given Well
        if try_str_from_series_or_none(plate_data, "Read Date") is None:
            return None

        location_id = try_str_from_series(plate_data, "Well")

        well_plate = try_str_from_series_or_none(plate_data, "Plate")

        image_feature_list = []
        for feature in IMAGE_FEATURES:
            image_dict = {
                str(feature): try_float_from_series_or_nan(plate_data, feature)
            }
            image_feature_list.append(image_dict)

        return Well(
            measurement_time=try_str_from_series(plate_data, "Read Date"),
            location_identifier=location_id,
            well_plate_identifier=well_plate,
            sample_identifier=f"{well_plate}_{location_id}",
            exposure_duration_setting=try_float_from_series_or_none(
                plate_data, "Exposure"
            ),
            illumination_setting=try_float_from_series_or_none(
                plate_data, "Preset Intensity"
            ),
            image_features=image_feature_list,
        )


@dataclass(frozen=True)
class WellList:
    wells: list[Well]

    def __iter__(self) -> Iterator[Well]:
        return iter(self.wells)

    @staticmethod
    def create(contents: MabtechApexContents) -> WellList:
        plate_data = contents.data
        well_list = []
        for _, well_data in plate_data.iterrows():
            well = Well.create(well_data)
            if well is not None:
                well_list.append(well)
        return WellList(wells=well_list)

from dataclasses import dataclass
from enum import Enum

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ScanPositionSettingPlateReader,
    TransmittedLightSetting,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType


class ExperimentType(Enum):
    FLUORESCENCE = "fluorescence"
    ABSORBANCE = "absorbance"
    LUMINESCENCE = "luminescence"
    OPTICAL_IMAGING = "optical imaging"


PLATEMAP_TO_SAMPLE_ROLE_TYPE = {
    "B": SampleRoleType.blank_role.value,
    "C": SampleRoleType.control_sample_role.value,
    "S": SampleRoleType.standard_sample_role.value,
    "U": SampleRoleType.unknown_sample_role.value,
    "E": SampleRoleType.control_sample_role.value,
    "ZL": SampleRoleType.control_sample_role.value,
    "ZH": SampleRoleType.control_sample_role.value,
    "LB": SampleRoleType.control_sample_role.value,
    "LC": SampleRoleType.control_sample_role.value,
    "LH": SampleRoleType.control_sample_role.value,
}


SCAN_POSITION_CONVERTION = {
    "TOP": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
    "BOTTOM": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
}


TRANSMITTED_LIGHT_CONVERTION = {
    "BRIGHTFIELD": TransmittedLightSetting.lightfield,
    "DARKFIELD": TransmittedLightSetting.darkfield,
    "PHASE CONTRAST": TransmittedLightSetting.phase_contrast,
}


@dataclass(frozen=True)
class WellPosition:
    column: str
    row: str

    def __repr__(self) -> str:
        return self.row + self.column

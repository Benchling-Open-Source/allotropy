from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ScanPositionSettingPlateReader,
    TransmittedLightSetting,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType

SOFTWARE_NAME = "Kaleido"
DEVICE_IDENTIFIER = "EnSight"
MODEL_NUMBER = "EnSight"
PRODUCT_MANUFACTURER = "Revvity"
MAGNIFICATION_SETTING = 4

CHANNEL_COLUMNS_ERROR = "Expected every Channel be followed by: Excitation wavelength [nm], Excitation Power [%], Exposure Time [ms], Additional Focus offset [mm]"


PLATEMAP_TO_SAMPLE_ROLE_TYPE = {
    "B": SampleRoleType.blank_role,
    "C": SampleRoleType.control_sample_role,
    "S": SampleRoleType.standard_sample_role,
    "U": SampleRoleType.unknown_sample_role,
    "E": SampleRoleType.control_sample_role,
    "ZL": SampleRoleType.control_sample_role,
    "ZH": SampleRoleType.control_sample_role,
    "LB": SampleRoleType.control_sample_role,
    "LC": SampleRoleType.control_sample_role,
    "LH": SampleRoleType.control_sample_role,
}


SCAN_POSITION_CONVERSION = {
    "TOP": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
    "BOTTOM": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
}


TRANSMITTED_LIGHT_CONVERSION = {
    "BRIGHTFIELD": TransmittedLightSetting.brightfield,
    "DARKFIELD": TransmittedLightSetting.darkfield,
    "PHASE CONTRAST": TransmittedLightSetting.phase_contrast,
}

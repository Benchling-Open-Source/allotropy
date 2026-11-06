from allotropy.allotrope.models.adm.plate_reader.rec._2026._03.plate_reader import (
    SampleRoleType,
)

DISPLAY_NAME = "BMG Labtech SMART Control"
PRODUCT_MANUFACTURER = "BMG LABTECH"
SOFTWARE_NAME = "SMART Control"
DEVICE_TYPE = "fluorescence detector"

TARGET_TEMPERATURE = "Target temperature [°C]"
SAMPLE_ROLE_TYPE_MAPPING = {
    "Blank": SampleRoleType.blank_role,
    "Standard": SampleRoleType.standard_sample_role,
    "Sample": SampleRoleType.sample_role,
}

from allotropy.allotrope.models.adm.plate_reader.rec._2026._03.plate_reader import (
    SampleRoleType,
)

DETECTION_TYPE = "luminescence"
DEVICE_TYPE = "luminescence detector"
SOFTWARE_NAME = "MSD Workbench"

SAMPLE_ROLE_TYPE_MAPPING = {
    "c": SampleRoleType.control_sample_role,
    "s": SampleRoleType.standard_sample_role,
    "b": SampleRoleType.blank_role,
    "u": SampleRoleType.unknown_sample_role,
}

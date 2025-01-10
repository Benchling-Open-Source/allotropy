from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType

DETECTION_TYPE = "luminescence"
DEVICE_TYPE = "luminescence detector"
SOFTWARE_NAME = "MSD Workbench"

SAMPLE_ROLE_TYPE_MAPPING = {
    "c": SampleRoleType.control_sample_role,
    "s": SampleRoleType.standard_sample_role,
    "b": SampleRoleType.blank_role,
    "u": SampleRoleType.unknown_sample_role,
}

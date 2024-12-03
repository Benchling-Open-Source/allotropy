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

POSSIBLE_WELL_COUNTS = [1, 2, 4, 6, 8, 12, 24, 48, 72, 96, 384, 1536, 3456]

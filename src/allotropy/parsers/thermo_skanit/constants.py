""" Constants file for Thermo SkanIt"""
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType

SAMPLE_ROLE_MAPPINGS = {
    "Un": SampleRoleType.unknown_sample_role,
    "Std": SampleRoleType.standard_sample_role,
    "Blank": SampleRoleType.blank_role,
    "Ctrl": SampleRoleType.control_sample_role,
}
DEVICE_TYPE = "plate reader"

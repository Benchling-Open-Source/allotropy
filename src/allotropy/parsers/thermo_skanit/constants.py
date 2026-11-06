""" Constants file for Thermo SkanIt"""
from allotropy.allotrope.models.adm.plate_reader.rec._2025._03.plate_reader import (
    SampleRoleType,
)

SAMPLE_ROLE_MAPPINGS = {
    "Un": SampleRoleType.unknown_sample_role,
    "Std": SampleRoleType.standard_sample_role,
    "Blank": SampleRoleType.blank_role,
    "Ctrl": SampleRoleType.control_sample_role,
}
DEVICE_TYPE = "plate reader"

PLATE_IDENTIFIER_PATTERN = r"\b(?:\w+\s+)?plate(?:\s+\d+)?\b"

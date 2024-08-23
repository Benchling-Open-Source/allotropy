from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType

SOFTWARE_NAME = "“Bio-Plex Manager"
PRODUCT_MANUFACTURER = "Bio-Rad"
DEVICE_TYPE = "multi analyte profiling analyzer"
CONTAINER_TYPE = "well plate"

ERROR_MAPPING = {
    "1": "Low bead number",
    "2": "Aggregated beads",
    "3": "Classify efficiency",
    "4": "Region selection",
    "5": "Platform temperature",
}

SAMPLE_ROLE_TYPE_MAPPING = {
    "Blank": SampleRoleType.blank_role,
    "Control": SampleRoleType.control_sample_role,
    "Standard": SampleRoleType.standard_sample_role,
    "Unknown": SampleRoleType.unknown_sample_role,
}

EXPECTED_TAGS = [
    "Samples",
    "NativeDocumentLocation",
    "Description",
    "PlateDimensions",
    "Wells",
]

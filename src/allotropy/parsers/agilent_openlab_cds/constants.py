"""Constants file for Agilent OpenLab CDS Adapter"""

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType

DISPLAY_NAME = "Agilent OpenLab CDS"
PRODUCT_MANUFACTURER = "Agilent"
SAMPLE_ROLE_TYPE = {
    "blank role": SampleRoleType.blank_role,
    "sample role": SampleRoleType.sample_role,
}

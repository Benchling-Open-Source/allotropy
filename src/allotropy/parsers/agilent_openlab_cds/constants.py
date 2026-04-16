"""Constants file for Agilent OpenLab CDS Adapter"""

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    SampleRoleType,
)

DISPLAY_NAME = "Agilent OpenLab CDS"
PRODUCT_MANUFACTURER = "Agilent"
SAMPLE_ROLE_TYPE = {
    "Blank": SampleRoleType.blank_role.value,
    "Sample": SampleRoleType.sample_role.value,
}

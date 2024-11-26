from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType

BRAND_NAME = "Biacore"
PRODUCT_MANUFACTURER = "Cytiva"
DISPLAY_NAME = "Cytiva Biacore T200 Control"
SURFACE_PLASMON_RESONANCE = "surface plasmon resonance"
DEVICE_TYPE = "binding affinity analyzer"

PLATEMAP_TO_SAMPLE_ROLE_TYPE = {
    "blank role":SampleRoleType.blank_role,
    "sample role": SampleRoleType.sample_role
}

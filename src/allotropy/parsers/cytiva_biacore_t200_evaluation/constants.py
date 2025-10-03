from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType

DEVICE_IDENTIFIER = "Biacore"
PRODUCT_MANUFACTURER = "Cytiva"
MODEL_NUMBER = "T200"
DISPLAY_NAME = "Cytiva Biacore T200 Evaluation"
SURFACE_PLASMON_RESONANCE = "surface plasmon resonance"
DEVICE_TYPE = "binding affinity analyzer"

SAMPLE_ROLE_TYPE = {
    "blank role": SampleRoleType.blank_role.value,
    "sample role": SampleRoleType.sample_role.value,
}

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import (
    ContainerType,
    SampleRoleType,
)

SAMPLE_ROLE_TYPES_MAP = {
    "Unkn": SampleRoleType.unknown_sample_role,
    "Std": SampleRoleType.standard_sample_role,
    "NTC": SampleRoleType.control_sample_role,
    "Pos": SampleRoleType.control_sample_role,
    "Neg": SampleRoleType.control_sample_role,
    "NRT": SampleRoleType.control_sample_role,
}

DISPLAY_NAME = "Bio-Rad CFX Maestro"
DEVICE_TYPE = "qPCR"

PRODUCT_MANUFACTURER = "Bio-Rad"
SOFTWARE_NAME = "CFX Maestro"
CONTAINER_TYPE = ContainerType.well_plate
EXPERIMENT_TYPE = "comparative CT qPCR experiment"

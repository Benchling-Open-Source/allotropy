from enum import Enum

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import (
    ContainerType,
    SampleRoleType,
)


class ExperimentType(str, Enum):
    genotyping_qPCR_experiment = "genotyping qPCR experiment"
    relative_standard_curve_qPCR_experiment = "relative standard curve qPCR experiment"
    melt_curve_qPCR_experiment = "melt curve qPCR experiment"
    comparative_CT_qPCR_experiment = "comparative CT qPCR experiment"
    standard_curve_qPCR_experiment = "standard curve qPCR experiment"
    qPCR_experiment = "qPCR experiment"
    presence_absence_qPCR_experiment = "presence/absence qPCR experiment"
    primary_analysis_experiment = "primary analysis experiment"


SAMPLE_ROLE_TYPES_MAP = {
    "NTC": SampleRoleType.control_sample_role,
    "STANDARD": SampleRoleType.standard_sample_role,
    "UNKNOWN": SampleRoleType.unknown_sample_role,
    "POSITIVE_CONTROL": SampleRoleType.control_sample_role,
    "IPC": SampleRoleType.control_sample_role,
    "BLOCKED_IPC": SampleRoleType.control_sample_role,
    "BLOCKEDIPC": SampleRoleType.control_sample_role,
    "PC_ALLELE_1": SampleRoleType.control_sample_role,
    "PC_ALLELE_2": SampleRoleType.control_sample_role,
    "PC_ALLELE_BOTH": SampleRoleType.control_sample_role,
    "POSITIVE_11": SampleRoleType.control_sample_role,
    "POSITIVE_22": SampleRoleType.control_sample_role,
    "POSITIVE_12": SampleRoleType.control_sample_role,
    "Accuracy Control": SampleRoleType.control_sample_role,
}
DEVICE_TYPE = "qPCR"
SOFTWARE_NAME = "Thermo QuantStudio"
SOFTWARE_VERSION = "1.0"
DATA_SYSTEM_INSTANCE_IDENTIFIER = "localhost"
CONTAINER_TYPE = ContainerType.PCR_reaction_block

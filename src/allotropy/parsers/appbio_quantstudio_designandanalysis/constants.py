from enum import Enum

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import ContainerType


# Experiment type was an enum in the BENCHLING/2023/09 version of the qpcr schema, but
# is now just a string field without enum validation. We are keeping this because quantstudio
# adapters have logic around the enum class, but we don't include it in the mapper because is
# not used for validation.
class ExperimentType(str, Enum):
    genotyping_qpcr_experiment = "genotyping qPCR experiment"
    relative_standard_curve_qpcr_experiment = "relative standard curve qPCR experiment"
    melt_curve_qpcr_experiment = "melt curve qPCR experiment"
    comparative_ct_qpcr_experiment = "comparative CT qPCR experiment"
    standard_curve_qpcr_experiment = "standard curve qPCR experiment"
    qpcr_experiment = "qPCR experiment"
    presence_absence_qpcr_experiment = "presence/absence qPCR experiment"
    primary_analysis_experiment = "primary analysis experiment"


DEVICE_TYPE = "qPCR"
PRODUCT_MANUFACTURER = "ThermoFisher Scientific"
DATA_SYSTEM_INSTANCE_IDENTIFIER = "localhost"
CONTAINER_TYPE = ContainerType.PCR_reaction_block

RT_PCR_SOFTWARE_NAME = "Design & Analysis Software"
RT_PCR_SOFTWARE_VERSION = "1.x"

from dataclasses import dataclass


@dataclass(frozen=True)
class CalculatedDataConfig:
    name: str
    key: str
    unit: str
    feature: str | None = None


CONFIGS: list[CalculatedDataConfig] = [
    CalculatedDataConfig(
        name="CI (95%)", key="CI (95%)", unit="%", feature="Positive Partition Count"
    ),
    CalculatedDataConfig(
        name="SD", key="SD", unit="(unitless)", feature="Number Concentration (#/μL)"
    ),
    CalculatedDataConfig(
        name="CV%", key="CV%", unit="%", feature="Number Concentration (#/μL)"
    ),
    CalculatedDataConfig(
        name="Mean Concentration",
        key="Mean conc. [copies/μL]",
        unit="#/μL",
        feature="Mean Concentration (#/μL)",
    ),
]

CONFIGS_KEYS: set[str] = {config.key for config in CONFIGS}


BRAND_NAME = "Qiacuity Digital PCR System"
PRODUCT_MANUFACTURER = "Qiagen"
SOFTWARE_NAME = "Qiacuity Software Suite"
DEVICE_TYPE = "dPCR"
DEVICE_IDENTIFIER = "Qiacuity dPCR"

SAMPLE_ROLE_TYPE_MAPPING = {
    "Sample": "Sample Role",
    "Control": "Control Sample Role",
    "Non Template Control": "Blank Role",
}

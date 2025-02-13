from pathlib import Path
from typing import Any

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_chromeleon import constants


def create_metadata(
    first_injection: dict[str, Any],
    sequence: dict[str, Any],
    device_information: dict[str, Any],
    file_path: str,
) -> Metadata:
    return Metadata(
        asset_management_identifier=first_injection.get(
            "Precondition system instrument name", NOT_APPLICABLE
        ),
        software_name=constants.SOFTWARE_NAME,
        software_version=NOT_APPLICABLE,
        file_name=Path(file_path).name,
        unc_path=file_path,
        description=first_injection.get("description"),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        pump_model_number=device_information.get("pump model number"),
        detector_model_number=device_information.get("uv model number"),
        sampler_model_number=device_information.get("sampler model number"),
        lc_agg_custom_info={
            "Sequence Creation Time": sequence.get("sequence creation time"),
            "Sequence Directory": sequence.get("sequence directory"),
            "Sequence Name": sequence.get("sequence name"),
            "Sequence Update operator": sequence.get("sequence update operator"),
            "Sequence Update Time": sequence.get("sequence update time"),
            "Number of Injections": 0,
        },
    )


def create_measurement_groups(
    injections: list[dict[str, Any]],
    sequence: dict[str, Any],
    device_information: dict[str, Any],
) -> list[MeasurementGroup]:
    pass

from __future__ import annotations

from pathlib import Path

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
)
from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import get_key_or_error
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_qubit4 import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str

EMISSION_WAVELENGTH_TO_MEASUREMENT_COLUMN = {
    "green": "Green RFU",
    "far red": "Far Red RFU",
}


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    std_1_rfu = data.get(float, "Std 1 RFU", validate=SeriesData.NOT_NAN)
    std_2_rfu = data.get(float, "Std 2 RFU", validate=SeriesData.NOT_NAN)
    std_3_rfu = data.get(float, "Std 3 RFU", validate=SeriesData.NOT_NAN)
    return MeasurementGroup(
        measurement_time=data[str, "Test Date"],
        experiment_type=data.get(str, "Assay Name"),
        measurements=[
            Measurement(
                type_=MeasurementType.FLUORESCENCE,
                identifier=random_uuid_str(),
                fluorescence=data[
                    float,
                    get_key_or_error(
                        "wavelength",
                        data.get(str, "Emission", "").lower(),
                        EMISSION_WAVELENGTH_TO_MEASUREMENT_COLUMN,
                    ),
                ],
                batch_identifier=data.get(str, "Run ID"),
                sample_identifier=data[str, "Test Name"],
                sample_volume_setting=data.get(
                    float, "Sample Volume (μL)", validate=SeriesData.NOT_NAN
                ),
                excitation_wavelength_setting=data.get(str, "Excitation"),
                emission_wavelength_setting=data[str, "Emission"],
                dilution_factor_setting=data.get(
                    float, "Dilution Factor", validate=SeriesData.NOT_NAN
                ),
                original_sample_concentration=data.get(
                    float, "Original sample conc.", NaN
                ),
                original_sample_concentration_unit=data.get(
                    str, "Units_Original sample conc."
                ),
                sample_custom_info={
                    "qubit tube concentration": {
                        "value": data.get(float, "Qubit® tube conc.", NaN),
                        "unit": data.get(str, "Units_Qubit® tube conc.", UNITLESS),
                    },
                    "standard 1 concentration": {"value": std_1_rfu, "unit": "RFU"}
                    if std_1_rfu is not None
                    else None,
                    "standard 2 concentration": {
                        "value": std_2_rfu,
                        "unit": "RFU",
                    }
                    if std_2_rfu is not None
                    else None,
                    "standard 3 concentration": {
                        "value": std_3_rfu,
                        "unit": "RFU",
                    }
                    if std_3_rfu is not None
                    else None,
                },
                custom_info=data.get_unread(),
            )
        ],
    )


def create_metadata(file_path: str) -> Metadata:
    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
        device_identifier=NOT_APPLICABLE,
        model_number=constants.MODEL_NUMBER,
        software_name=constants.QUBIT_SOFTWARE,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        brand_name=constants.BRAND_NAME,
        device_type=constants.DEVICE_TYPE,
        container_type=ContainerType.tube,
    )

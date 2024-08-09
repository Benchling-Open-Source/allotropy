from __future__ import annotations

import pandas as pd

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    NaN,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import get_key_or_error
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_qubit4 import constants
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str

EMISSION_WAVELENGTH_TO_MEASUREMENT_COLUMN = {
    "green": "Green RFU",
    "far red": "Far Red RFU",
}


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
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
                    float, "Sample Volume (µL)", validate=SeriesData.NOT_NAN
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
                qubit_tube_concentration=data.get(float, "Qubit® tube conc.", NaN),
                qubit_tube_concentration_units=data.get(str, "Units_Qubit® tube conc."),
                standard_1_concentration=data.get(
                    float, "Std 1 RFU", validate=SeriesData.NOT_NAN
                ),
                standard_2_concentration=data.get(
                    float, "Std 2 RFU", validate=SeriesData.NOT_NAN
                ),
                standard_3_concentration=data.get(
                    float, "Std 3 RFU", validate=SeriesData.NOT_NAN
                ),
            )
        ],
    )


def create_data(data_frame: pd.DataFrame, file_name: str) -> Data:
    return Data(
        metadata=Metadata(
            file_name=file_name,
            device_identifier=NOT_APPLICABLE,
            model_number=constants.MODEL_NUMBER,
            software_name=constants.QUBIT_SOFTWARE,
            product_manufacturer=constants.PRODUCT_MANUFACTURER,
            brand_name=constants.BRAND_NAME,
            device_type=constants.DEVICE_TYPE,
            container_type=ContainerType.tube,
        ),
        measurement_groups=map_rows(data_frame, create_measurement_group),
    )

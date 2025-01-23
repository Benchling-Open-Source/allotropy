from __future__ import annotations

from pathlib import Path

import pandas as pd

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    NaN,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_qubit_flex import constants
from allotropy.parsers.utils.pandas import df_to_series_data, map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    return MeasurementGroup(
        measurement_time=data[str, "Test Date"],
        experiment_type=data.get(str, "Assay Name"),
        measurements=[
            Measurement(
                type_=MeasurementType.FLUORESCENCE,
                identifier=random_uuid_str(),
                fluorescence=data[float, "Sample RFU"],
                batch_identifier=data.get(str, "Run ID"),
                sample_identifier=data[str, ["Sample ID", "Sample Name"]],
                location_identifier=data.get(str, "Well"),
                well_plate_identifier=data.get(str, "Plate Barcode"),
                sample_volume_setting=data.get(
                    float, "Sample Volume (uL)", validate=SeriesData.NOT_NAN
                ),
                excitation_wavelength_setting=data.get(str, "Excitation"),
                dilution_factor_setting=data.get(
                    float, "Dilution Factor", validate=SeriesData.NOT_NAN
                ),
                original_sample_concentration=data.get(
                    float, "Original Sample Conc.", NaN
                ),
                original_sample_concentration_unit=data.get(
                    str, "Original sample conc. units"
                ),
                sample_custom_info={
                    "last read standards": data.get(str, "Last Read Standards"),
                    "selected samples": data.get(int, "Selected Samples"),
                    "qubit tube concentration": {
                        "value": data.get(float, "Qubit Tube Conc.", NaN),
                        "unit": data.get(str, "Qubit tube conc. units", UNITLESS),
                    },
                    "standard 1 concentration": {
                        "value": data.get(
                            float, "Std 1 RFU", validate=SeriesData.NOT_NAN
                        ),
                        "unit": "RFU",
                    },
                    "standard 2 concentration": {
                        "value": data.get(
                            float, "Std 2 RFU", validate=SeriesData.NOT_NAN
                        ),
                        "unit": "RFU",
                    },
                    "standard 3 concentration": {
                        "value": data.get(
                            float, "Std 3 RFU", validate=SeriesData.NOT_NAN
                        ),
                        "unit": "RFU",
                    },
                },
                device_control_custom_info={
                    "operating minimum": {
                        "value": data.get(str, "Extended Low Range"),
                        "unit": "ng/µL",
                    },
                    "operating maximum": {
                        "value": data.get(str, "Extended High Range"),
                        "unit": "ng/µL",
                    },
                    "operating range": {
                        "value": data.get(
                            str, "Core Range", validate=SeriesData.NOT_NAN
                        ),
                        "unit": "ng/µL",
                    },
                },
                custom_info=data.get_unread(skip={"Software Version"}),
            )
        ],
    )


def create_data(df: pd.DataFrame, file_path: str) -> Data:
    header = df_to_series_data(df.head(1))
    # We read header info from a row in the table, so we don't need to read all keys from this SeriesData
    software_version = header.get(str, "Software Version")
    header.get_unread()
    return Data(
        metadata=Metadata(
            file_name=Path(file_path).name,
            unc_path=file_path,
            device_identifier=NOT_APPLICABLE,
            model_number=constants.MODEL_NUMBER,
            software_name=constants.SOFTWARE_NAME,
            software_version=software_version,
            product_manufacturer=constants.PRODUCT_MANUFACTURER,
            brand_name=constants.BRAND_NAME,
            device_type=constants.DEVICE_TYPE,
            container_type=ContainerType.tube,
        ),
        measurement_groups=map_rows(df, create_measurement_group),
    )

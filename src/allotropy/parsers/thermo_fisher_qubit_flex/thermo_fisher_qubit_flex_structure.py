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
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_qubit_flex import constants
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none

EMISSION_WAVELENGTH_TO_MEASUREMENT_COLUMN = {
    "green": "Green RFU",
    "far red": "Far Red RFU",
}


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    operating_minimum_range = data.get(str, "Extended Low Range")
    operating_minimum = (
        try_float_or_none(operating_minimum_range.split("-")[0])
        if operating_minimum_range
        else None
    )
    operating_maximum_range = data.get(str, "Extended High Range")
    operating_maximum = (
        try_float_or_none(operating_maximum_range.split("-")[-1])
        if operating_maximum_range
        else None
    )
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
                qubit_tube_concentration=data.get(float, "Qubit Tube Conc.", NaN),
                qubit_tube_concentration_units=data.get(str, "Qubit tube conc. units"),
                standard_1_concentration=data.get(
                    float, "Std 1 RFU", validate=SeriesData.NOT_NAN
                ),
                standard_2_concentration=data.get(
                    float, "Std 2 RFU", validate=SeriesData.NOT_NAN
                ),
                standard_3_concentration=data.get(
                    float, "Std 3 RFU", validate=SeriesData.NOT_NAN
                ),
                operating_minimum=operating_minimum,
                operating_maximum=operating_maximum,
                operating_range=data.get(
                    str, "Core Range", validate=SeriesData.NOT_NAN
                ),
                last_read_standards=data.get(str, "Test Date"),
                selected_samples=data.get(int, "Selected Samples"),
                reagent_lot_number=data.get(int, "Reagent Lot#"),
                calibrated_tubes=data.get(int, "Calibrated Tubes"),
            )
        ],
    )


def create_data(data_frame: pd.DataFrame, file_name: str) -> Data:
    return Data(
        metadata=Metadata(
            file_name=file_name,
            device_identifier=NOT_APPLICABLE,
            model_number=constants.MODEL_NUMBER,
            software_name=constants.SOFTWARE_NAME,
            product_manufacturer=constants.PRODUCT_MANUFACTURER,
            brand_name=constants.BRAND_NAME,
            device_type=constants.DEVICE_TYPE,
            container_type=ContainerType.tube,
        ),
        measurement_groups=map_rows(data_frame, create_measurement_group),
    )

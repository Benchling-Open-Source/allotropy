""" Structure file for ThermoFisher Genesys 30 Adapter """
from __future__ import annotations

from datetime import datetime

import pandas as pd

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    DataCube,
    DataCubeComponent,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_genesys30 import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(header: SeriesData, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        device_type=constants.DEVICE_TYPE,
        device_identifier=NOT_APPLICABLE,
        model_number=constants.MODEL_NUMBER,
        software_name=constants.GENESYS_SOFTWARE,
        detection_type=header.get(str, "Mode"),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        brand_name=constants.BRAND_NAME,
        container_type=ContainerType.tube,
    )


def create_measurement_groups(
    header: SeriesData, data: pd.DataFrame
) -> list[MeasurementGroup]:
    experiment_name = header.get(str, "Scan")
    experiment_type, measurement_time = _get_experiment_type_and_time(experiment_name)
    return [
        MeasurementGroup(
            measurement_time=measurement_time,
            experiment_type=experiment_type,
            measurements=[
                Measurement(
                    type_=MeasurementType.ULTRAVIOLET_ABSORBANCE_SPECTRUM,
                    identifier=random_uuid_str(),
                    sample_identifier=NOT_APPLICABLE,
                    operating_minimum=header.get(float, "Lower"),
                    operating_maximum=header.get(float, "Upper"),
                    data_cube=DataCube(
                        label="absorption spectrum",
                        structure_dimensions=[
                            DataCubeComponent(
                                type_=FieldComponentDatatype.double,
                                concept="wavelength",
                                unit="nm",
                            )
                        ],
                        structure_measures=[
                            DataCubeComponent(
                                type_=FieldComponentDatatype.double,
                                concept="absorbance",
                                unit="mAU",
                            )
                        ],
                        dimensions=[data["wavelength(nm)"].tolist()],
                        measures=[data["ABS"].tolist()],
                    ),
                ),
            ],
        ),
    ]


def _get_experiment_type_and_time(experiment_name: str | None) -> tuple[str, str]:
    """
    Gets data and time of measurement from the experiment name
    :param experiment_name: The name of the experiment conducted
    :return: Experiment type and measurement time
    """
    if experiment_name:
        experiment_type, date, time = experiment_name.split("_", 2)
        time = time.split(".")[0]
        timestamp = date + time

        measurement_time = (
            datetime.strptime(timestamp, "%Y%m%d%H%M%S")
            .astimezone()
            .strftime("%d-%m-%Y %I:%M %p")
        )
        return experiment_type, measurement_time
    else:
        raise AllotropeConversionError(constants.MEASUREMENT_TIME_MISSING)

""" Structure file for ThermoFisher Genesys 30 Adapter """
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_genesys30 import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(header: SeriesData, file_path: str) -> Metadata:
    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
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
                        measures=[data["ABS"].astype(float).tolist()],
                    ),
                    device_control_custom_info={
                        "operating minimum": {
                            "value": header.get(float, "Lower"),
                            "unit": "nm",
                        },
                        "operating maximum": {
                            "value": header.get(float, "Upper"),
                            "unit": "nm",
                        },
                    },
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

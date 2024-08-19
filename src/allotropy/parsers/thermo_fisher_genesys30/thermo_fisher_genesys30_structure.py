""" Structure file for ThermoFisher Genesys 30 Adapter """
from __future__ import annotations

from datetime import datetime
import io

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    DataCube,
    DataCubeComponent,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.thermo_fisher_genesys30 import constants
from allotropy.parsers.utils.pandas import df_to_series_data, read_csv
from allotropy.parsers.utils.uuids import random_uuid_str


def create_data(named_file_contents: NamedFileContents) -> Data:
    """
    Structures the named_file_contents according to the mapper file
    :param named_file_contents: The contents of the file to convert
    :return: The data according to spectrophotometer data mapper
    """
    filename = named_file_contents.original_file_name

    lines = read_to_lines(named_file_contents)
    reader = LinesReader(lines)

    if filename.endswith(".csv"):
        metadata_list = [line for line in reader.pop_until("^,,") if line]
        reader.drop_until_inclusive(",,")
        delimiter = ","
    elif filename.endswith(".tsv"):
        metadata_list = list(reader.pop_until_empty())
        reader.drop_until_inclusive("")
        delimiter = "\t"
    else:
        message = f"{constants.UNSUPPORTED_FILE_FORMAT_ERROR} {filename}"
        raise AllotropeConversionError(message)

    rawdata_list = list(reader.pop_until_empty())
    rawdata_string = io.StringIO("\n".join(rawdata_list))
    rawdata_dataframe = read_csv(rawdata_string, header=0, delimiter=delimiter)

    metadata_string = io.StringIO("\n".join(metadata_list))
    metadata_dataframe = (
        read_csv(
            metadata_string,
            header=None,
            delimiter=delimiter,
            keep_default_na=False,
            index_col=0,
        )
        .astype(str)
        .T
    )
    metadata_dataframe.columns = metadata_dataframe.columns.str.strip()
    rawdata_dataframe.columns = rawdata_dataframe.columns.astype(str).str.strip()

    metadata_dataframe = metadata_dataframe.head(1)

    metadata = df_to_series_data(metadata_dataframe, "Failed to parser header data")

    experiment_name = metadata.get(str, "Scan")

    experiment_type, measurement_time = get_experiment_type_and_time(experiment_name)

    return Data(
        metadata=Metadata(
            file_name=filename,
            device_type=constants.DEVICE_TYPE,
            device_identifier=NOT_APPLICABLE,
            model_number=constants.MODEL_NUMBER,
            software_name=constants.GENESYS_SOFTWARE,
            detection_type=metadata.get(str, "Mode"),
            product_manufacturer=constants.PRODUCT_MANUFACTURER,
            brand_name=constants.BRAND_NAME,
            container_type=ContainerType.tube,
        ),
        measurement_groups=[
            MeasurementGroup(
                measurement_time=measurement_time,
                experiment_type=experiment_type,
                measurements=[
                    Measurement(
                        type_=MeasurementType.ULTRAVIOLET_ABSORBANCE_SPECTRUM,
                        identifier=random_uuid_str(),
                        sample_identifier=NOT_APPLICABLE,
                        operating_minimum=metadata.get(float, "Lower"),
                        operating_maximum=metadata.get(float, "Upper"),
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
                            dimensions=[rawdata_dataframe["wavelength(nm)"].tolist()],
                            measures=[rawdata_dataframe["ABS"].tolist()],
                        ),
                    ),
                ],
            ),
        ],
    )


def get_experiment_type_and_time(experiment_name: str | None) -> tuple[str, str]:
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

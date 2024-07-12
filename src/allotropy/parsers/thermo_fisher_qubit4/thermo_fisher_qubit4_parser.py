""" Parser file for ThermoFisher Qubit 4 Adapter """

import re
from typing import Any, TypeVar

import numpy as np
import pandas as pd

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
    DataSystemDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    SampleDocument,
    SpectrophotometryAggregateDocument,
    SpectrophotometryDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrogramPerMicroliter,
    TQuantityValueMicrogramPerMilliliter,
    TQuantityValueMicroliter,
    TQuantityValueMilligramPerMilliliter,
    TQuantityValueNanogramPerMicroliter,
    TQuantityValueNanogramPerMilliliter,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_qubit4 import constants
from allotropy.parsers.thermo_fisher_qubit4.thermo_fisher_qubit4_reader import (
    ThermoFisherQubit4Reader,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

CONCENTRATION_UNIT_TO_TQUANTITY = {
    "μg/μL": TQuantityValueMicrogramPerMicroliter,
    "μg/mL": TQuantityValueMicrogramPerMilliliter,
    "mg/mL": TQuantityValueMilligramPerMilliliter,
    "ng/µL": TQuantityValueNanogramPerMicroliter,
    "ng/mL": TQuantityValueNanogramPerMilliliter,
}

DataType = TypeVar("DataType")


def get_concentration_value(
    data_frame: pd.DataFrame, column: str, units_column: str, row: int
) -> DataType | None:
    """
    Retrieves the value and its unit from the specified columns and row in the DataFrame. If units are not there, replace it with unitless unit.

    parameters:
    data_frame (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    units_column (str): The column name from which to retrieve the unit.
    row (int): The row index from which to retrieve the value.

    Returns:
    DataType | None: The concentration value converted to the appropriate data type, or None if the units are not available or invalid.
    """
    units = get_value(data_frame, units_column, row)
    if units is None:
        units = ""
    datatype = CONCENTRATION_UNIT_TO_TQUANTITY.get(units, TQuantityValueUnitless)
    return get_property_value(data_frame, column, row, datatype)


def get_property_value(
    data_frame: pd.DataFrame, column: str, row: int, datatype: type
) -> DataType | None:
    """
    Retrieves the value from a specified column and row in a DataFrame and converts it
    to the specified datatype.

    Parameters:
    data_frame (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    row (int): The row index from which to retrieve the value.
    datatype (type): The type to which the retrieved value should be converted.

    Returns:
    DataType | None: The value from the specified cell converted to the specified datatype.
         Returns None if the value is not found.
    """
    return (
        datatype(value=value) if (value := get_value(data_frame, column, row)) else None
    )


def get_value(data_frame: pd.DataFrame, column: str, row: int) -> Any | None:
    """
    Retrieves the value from a specified column and row in a DataFrame, handling NaNs
    and converting certain numpy types to native Python types.

    Parameters:
    data_frame (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    row (int): The row index from which to retrieve the value.

    Returns:
    Optional[Any]: The value from the specified cell converted to the appropriate Python type.
                   Returns None if the column does not exist or the value is NaN.
    """
    if column not in data_frame.columns:
        return None
    value = data_frame[column][row]

    if pd.isna(value):
        return None
    if isinstance(value, np.int64):
        return int(value)
    if isinstance(value, np.float64):
        return float(value)
    if isinstance(value, str) and re.match(r"^[-+]?[0-9]*\.?[0-9]+$", value):
        return float(value)
    return value


def get_value_not_none(dataframe: pd.DataFrame, column: str, row: int) -> Any:
    """
    Retrieves the value from a specified column and row in a DataFrame, ensuring the value is not None.

    Parameters:
    dataframe (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    row (int): The row index from which to retrieve the value.

    Returns:
    Any: The value from the specified cell.

    Raises:
    AllotropeConversionError: If the value is None.
    """
    value = get_value(dataframe, column, row)
    if value is None:
        msg = f"{constants.VALUE_ERROR} '{column}'."
        raise AllotropeConversionError(msg)
    return value


class ThermoFisherQubit4Parser(VendorParser):
    """
    Parser for the ThermoFisher Qubit 4 data files.

    This parser reads data from ThermoFisher Qubit 4 files and converts it into an Allotrope model. The main functionalities
    include extracting and converting specific measurement and device control data, as well as handling custom sample and
    device information.
    """

    @property
    def display_name(self) -> str:
        """
        Returns the display name of the parser.

        :return: The display name as a string.
        """
        return constants.DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        """
        Returns the release state of the parser.

        :return: The release state as a `ReleaseState` enum.
        """
        return ReleaseState.WORKING_DRAFT

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        """
        Converts the given named file contents to an Allotrope model.

        :param named_file_contents: The contents of the file to convert.
        :return: The converted Allotrope model.
        """
        return self._get_model(
            data=ThermoFisherQubit4Reader.read(named_file_contents),
            filename=named_file_contents.original_file_name,
        )

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        """
        Generates an Allotrope model from the given data and filename.

        :param data: The data as a pandas DataFrame.
        :param filename: The original filename.
        :return: The Allotrope model.
        """
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                spectrophotometry_document=self._get_spectrophotometry_document(data),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    software_name=constants.QUBIT_SOFTWARE,
                ),
                device_system_document=DeviceSystemDocument(
                    model_number=constants.MODEL_NUMBER,
                    device_identifier=NOT_APPLICABLE,
                    brand_name=constants.BRAND_NAME,
                    product_manufacturer=constants.PRODUCT_MANUFACTURER,
                ),
            ),
        )

    def _get_spectrophotometry_document(
        self, data: pd.DataFrame
    ) -> list[SpectrophotometryDocumentItem]:
        """
        Generates a list of spectrophotometry document items from the given data.

        :param data: The data as a pandas DataFrame.
        :return: A list of `SpectrophotometryDocumentItem`.
        """
        return [
            SpectrophotometryDocumentItem(
                measurement_aggregate_document=self._get_measurement_aggregate_document(
                    data, i
                )
            )
            for i in range(len(data.index))
        ]

    def _get_measurement_aggregate_document(
        self, data: pd.DataFrame, i: int
    ) -> MeasurementAggregateDocument:
        """
        Generates a measurement aggregate document from the given data and index.

        :param data: The data as a pandas DataFrame.
        :param i: The index of the row in the DataFrame.
        :return: The `MeasurementAggregateDocument`.
        """
        return MeasurementAggregateDocument(
            measurement_time=self._get_date_time(
                str(get_value_not_none(data, "Test Date", i))
            ),
            experiment_type=get_value(data, "Assay Name", i),
            container_type=ContainerType.tube,
            measurement_document=self._get_measurement_document(data, i),
        )

    def _get_measurement_document(
        self, data: pd.DataFrame, i: int
    ) -> list[
        FluorescencePointDetectionMeasurementDocumentItems
        | UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    ]:
        """
        Generates a list of measurement document items from the given data and index.

        :param data: The data as a pandas DataFrame.
        :param i: The index of the row in the DataFrame.
        :return: A list of `FluorescencePointDetectionMeasurementDocumentItems`.
        """
        return [
            FluorescencePointDetectionMeasurementDocumentItems(
                fluorescence=self._get_fluorescence_value(data, i),
                measurement_identifier=random_uuid_str(),
                sample_document=self._get_sample_document(data, i),
                device_control_aggregate_document=self._get_device_control_document(
                    data, i
                ),
            )
        ]

    def _get_fluorescence_value(
        self, data: pd.DataFrame, i: int
    ) -> TQuantityValueRelativeFluorescenceUnit:
        """
        Retrieves the fluorescence value from the given data and index based on the emission wavelength.

        :param data: The data as a pandas DataFrame.
        :param i: The index of the row in the DataFrame.
        :return: The `TQuantityValueRelativeFluorescenceUnit`.
        :raises AllotropeConversionError: If the emission wavelength is unsupported.
        """
        emission_wavelength = get_value(data, "Emission", i)
        if emission_wavelength is not None and emission_wavelength.lower() == "green":
            value = TQuantityValueRelativeFluorescenceUnit(
                value=get_value_not_none(data, "Green RFU", i)
            )
            return value
        elif (
            emission_wavelength is not None and emission_wavelength.lower() in "far red"
        ):
            value = TQuantityValueRelativeFluorescenceUnit(
                value=get_value_not_none(data, "Far Red RFU", i)
            )
            return value
        else:
            message = f"{constants.UNSUPPORTED_WAVELENGTH_ERROR} {emission_wavelength}"
            raise AllotropeConversionError(message)

    def _get_sample_document(self, data: pd.DataFrame, i: int) -> SampleDocument:
        """
        Generates a sample document from the given data and index.

        :param data: The data as a pandas DataFrame.
        :param i: The index of the row in the DataFrame.
        :return: The `SampleDocument`.
        """
        sample_custom_document = {
            "original sample concentration": get_concentration_value(
                data, "Original sample conc.", "Units_Original sample conc.", i
            ),
            "qubit tube concentration": get_concentration_value(
                data, "Qubit® tube conc.", "Units_Qubit® tube conc.", i
            ),
            "standard 1 concentration": get_property_value(
                data, "Std 1 RFU", i, TQuantityValueRelativeFluorescenceUnit
            ),
            "standard 2 concentration": get_property_value(
                data, "Std 2 RFU", i, TQuantityValueRelativeFluorescenceUnit
            ),
            "standard 3 concentration": get_property_value(
                data, "Std 3 RFU", i, TQuantityValueRelativeFluorescenceUnit
            ),
        }

        if all(value is None for value in sample_custom_document.values()):
            return SampleDocument(
                sample_identifier=get_value_not_none(data, "Test Name", i),
                batch_identifier=str(get_value(data, "Run ID", i)),
            )
        else:
            return add_custom_information_document(
                SampleDocument(
                    sample_identifier=get_value_not_none(data, "Test Name", i),
                    batch_identifier=str(get_value(data, "Run ID", i)),
                ),
                sample_custom_document,
            )

    def _get_device_control_document(
        self, data: pd.DataFrame, i: int
    ) -> FluorescencePointDetectionDeviceControlAggregateDocument:
        """
        Generates a device control aggregate document from the given data and index.

        :param data: The data as a pandas DataFrame.
        :param i: The index of the row in the DataFrame.
        :return: The `FluorescencePointDetectionDeviceControlAggregateDocument`.
        """
        custom_device_document = {
            "sample volume setting": get_property_value(
                data, "Sample Volume (µL)", i, TQuantityValueMicroliter
            ),
            "excitation setting": get_value(data, "Excitation", i),
            "emission setting": get_value(data, "Emission", i),
            "dilution factor": get_property_value(
                data, "Dilution Factor", i, TQuantityValueUnitless
            ),
        }
        if all(value is None for value in custom_device_document.values()):
            return FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    FluorescencePointDetectionDeviceControlDocumentItem(
                        device_type=constants.DEVICE_TYPE
                    )
                ]
            )
        else:
            return FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        FluorescencePointDetectionDeviceControlDocumentItem(
                            device_type=constants.DEVICE_TYPE
                        ),
                        custom_device_document,
                    )
                ]
            )

""" Parser file for Thermo Fisher Qubit Flex Adapter"""
from __future__ import annotations

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
    TQuantityValuePicogramPerMilliliter,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_qubit_flex import constants
from allotropy.parsers.thermo_fisher_qubit_flex.thermo_fisher_qubit_flex_reader import (
    ThermoFisherQubitFlexReader,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

DataType = TypeVar("DataType")

CONCENTRATION_UNIT_TO_TQUANTITY = {
    "ug/uL": TQuantityValueMicrogramPerMicroliter,
    "ug/mL": TQuantityValueMicrogramPerMilliliter,
    "mg/mL": TQuantityValueMilligramPerMilliliter,
    "ng/uL": TQuantityValueNanogramPerMicroliter,
    "ng/mL": TQuantityValueNanogramPerMilliliter,
    "pg/uL": TQuantityValuePicogramPerMilliliter,
}


def _get_concentration_value(
    data_frame: pd.DataFrame, column: str, units_column: str, row: int
) -> DataType | None:
    """
    Retrieves the value and its unit from the specified columns and row in the DataFrame. If units are not there, replace it with unitless" unit.

    parameters:
    data_frame (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    units_column (str): The column name from which to retrieve the unit.
    row (int): The row index from which to retrieve the value.

    Returns:
    Optional[DataType|None]: The concentration value converted to the appropriate data type, or None if the units are not available or invalid.
    """
    units = _get_value(data_frame, units_column, row)
    if units is None:
        units = ""
    datatype = CONCENTRATION_UNIT_TO_TQUANTITY.get(units, TQuantityValueUnitless)
    return _get_property_value(data_frame, column, row, datatype)


def _get_value(data_frame: pd.DataFrame, column: str, row: int) -> Any | None:
    """
    Retrieves the value from a specified column and row in a DataFrame, handling NaNs
    and converting certain numpy types to native Python types.

    Parameters:
    data_frame (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    row (int): The row index from which to retrieve the value.

    Returns:
    Optional[Any|None]: The value from the specified cell converted to the appropriate Python type.
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
    return value


def _get_property_value(
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
    Datatype (Any|None): The value from the specified cell converted to the specified datatype.
         Returns None if the value is not found.
    """
    return (
        datatype(value=value)
        if (value := _get_value(data_frame, column, row))
        else None
    )


def _get_value_not_none(dataframe: pd.DataFrame, column: str, row: int) -> Any:
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
    value = _get_value(dataframe, column, row)
    if value is None:
        msg = f"{constants.VALUE_ERROR} '{column}'."
        raise AllotropeConversionError(msg)
    return value


def _get_property_value_not_none(
    data_frame: pd.DataFrame, column: str, row: int, datatype: type
) -> DataType | None:
    """
    Retrieves the value from a specified column and row in a DataFrame and converts it
    to the specified datatype. If the value is not in the respective column it throws the Allotrope Exception.

    Parameters:
    data_frame (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    row (int): The row index from which to retrieve the value.
    datatype (type): The type to which the retrieved value should be converted.

    Returns:
    Datatype(Any): The value from the specified cell converted to the specified datatype.

    Raises:
    AllotropeConversionError: If the value is None.
    """
    return (
        datatype(value=value)
        if (value := _get_value_not_none(data_frame, column, row))
        else None
    )


class ThermoFisherQubitFlexParser(VendorParser):
    """
    A class provides the allotrope model of the Thermo Fisher Qubit Flex files
    """

    @property
    def display_name(self) -> str:
        """
        Provide the display name of the Adapter

        Returns: the Adapter display name as string
        """
        return constants.DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        """
        Provide the Release state of the Adapter
        """
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        """
        Reads the content of the provided named file and returns it as Model

        Parameters:
        named_file_contents: contents of the provided named file

        Returns: the Model of the provided named file
        """
        return self._get_model(
            data=ThermoFisherQubitFlexReader.read(named_file_contents),
            filename=named_file_contents.original_file_name,
        )

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        """
        Reads the content of the provided named file and returns it as Model

        Parameters:
        data: dataframe of the provided named file
        filename: original filename of the provided named file

        Returns: the Model of the provided named file
        """
        software_version = _get_value(data, "Software Version", (len(data.index) - 1))
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                spectrophotometry_document=self._get_spectrophotometry_document(data),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=constants.SOFTWARE_NAME,
                    software_version=software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
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
        Reads the content of the provided named file and returns it as a list.

        Parameters:
        data: dataframe of the provided named file
        i: index of the dataframe

        Returns: the spectrophotometry document list
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
        Reads the content of the provided named file and returns it as a dictionary.

        Parameters:
        data: dataframe of the provided named file
        i: index of the dataframe

        Returns: the measurement aggregate document dictionary
        """
        return MeasurementAggregateDocument(
            measurement_time=self._get_date_time(
                str(_get_value_not_none(data, "Test Date", i))
            ),
            experiment_type=_get_value(data, "Assay Name", i),
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
        Reads the content of the provided named file and returns it as a dictionary.

        Parameters:
        data: dataframe of the provided named file
        i: index of the dataframe

        Returns: the measurement document dictionary
        """
        measurement_custom_document = {
            "reagent lot number": _get_value(data, "Reagent Lot#", i),
            "calibrated tubes": _get_value(data, "Calibrated Tubes", i),
        }
        # Check if all values in sample_custom_document are None
        if all(value is None for value in measurement_custom_document.values()):
            return [
                FluorescencePointDetectionMeasurementDocumentItems(
                    fluorescence=self._get_fluorescence_value(data, i),
                    measurement_identifier=random_uuid_str(),
                    sample_document=self._get_sample_document(data, i),
                    device_control_aggregate_document=self._get_device_control_document(
                        data, i
                    ),
                ),
            ]

        else:
            return [
                add_custom_information_document(
                    FluorescencePointDetectionMeasurementDocumentItems(
                        fluorescence=self._get_fluorescence_value(data, i),
                        measurement_identifier=random_uuid_str(),
                        sample_document=self._get_sample_document(data, i),
                        device_control_aggregate_document=self._get_device_control_document(
                            data, i
                        ),
                    ),
                    measurement_custom_document,
                )
            ]

    def _get_fluorescence_value(self, data: pd.DataFrame, i: int) -> Any:
        """
        Reads the content of the provided named file and returns the fluorescence value as string.

        Parameters:
        data: dataframe of the provided named file
        i: index of the dataframe

        Returns: the fluorescence value as string
        """
        value = _get_property_value_not_none(
            data, "Sample RFU", i, TQuantityValueRelativeFluorescenceUnit
        )
        return value

    def _get_sample_document(self, data: pd.DataFrame, i: int) -> SampleDocument:
        """
        Reads the content of the provided named file and returns it as a dictionary.

        Parameters:
        data: dataframe of the provided named file
        i: index of the dataframe

        Returns: the sample document dictionary
        """
        sample_id = _get_value(data, "Sample ID", i)
        location_id = _get_value(data, "Well", i)
        well_plate_id = _get_value(data, "Plate Barcode", i)
        if sample_id is None:
            sample_id = _get_value_not_none(data, "Sample Name", i)
        sample_custom_document = {
            "original sample concentration": _get_concentration_value(
                data, "Original Sample Conc.", "Original sample conc. units", i
            ),
            "qubit tube concentration": _get_concentration_value(
                data, "Qubit Tube Conc.", "Qubit tube conc. units", i
            ),
            "standard 1 concentration": _get_property_value(
                data, "Std 1 RFU", i, TQuantityValueRelativeFluorescenceUnit
            ),
            "standard 2 concentration": _get_property_value(
                data, "Std 2 RFU", i, TQuantityValueRelativeFluorescenceUnit
            ),
            "standard 3 concentration": _get_property_value(
                data, "Std 3 RFU", i, TQuantityValueRelativeFluorescenceUnit
            ),
            "last read standards": self._get_date_time(
                str(_get_value(data, "Test Date", i))
            ),
            "selected samples": _get_value(data, "Selected Samples", i),
        }
        if all(value is None for value in sample_custom_document.values()):
            return SampleDocument(
                sample_identifier=sample_id,
                batch_identifier=str(_get_value(data, "Run ID", i)),
                location_identifier=location_id,
                well_plate_identifier=well_plate_id,
            )
        else:
            return add_custom_information_document(
                SampleDocument(
                    sample_identifier=sample_id,
                    batch_identifier=str(_get_value(data, "Run ID", i)),
                    location_identifier=location_id,
                    well_plate_identifier=well_plate_id,
                ),
                sample_custom_document,
            )

    def _get_device_control_document(
        self, data: pd.DataFrame, i: int
    ) -> FluorescencePointDetectionDeviceControlAggregateDocument:
        """
        Reads the content of the provided named file and returns it as a dictionary.

        Parameters:
        data: dataframe of the provided named file
        i: index of the dataframe

        Returns: the device control document dictionary
        """
        custom_device_document = {
            "sample volume setting": _get_property_value(
                data, "Sample Volume (uL)", i, TQuantityValueMicroliter
            ),
            "operating minimum": _get_property_value(
                data, "Extended Low Range", i, TQuantityValueNanogramPerMicroliter
            ),
            "operating range": _get_property_value(
                data, "Core Range", i, TQuantityValueNanogramPerMicroliter
            ),
            "operating maximum": _get_property_value(
                data, "Extended High Range", i, TQuantityValueNanogramPerMicroliter
            ),
            "excitation setting": _get_value(data, "Excitation", i),
            "dilution factor": _get_property_value(
                data, "Dilution Factor", i, TQuantityValueUnitless
            ),
        }
        if all(value is None for value in custom_device_document.values()):
            return FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    FluorescencePointDetectionDeviceControlDocumentItem(
                        device_type=constants.DEVICE_TYPE
                    ),
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

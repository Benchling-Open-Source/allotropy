""" Parser file for Roche Cedex HiRes Instrument """
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypeVar

import numpy as np
import pandas as pd

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    CellCountingAggregateDocument,
    CellCountingDetectorDeviceControlAggregateDocument,
    CellCountingDetectorMeasurementDocumentItem,
    CellCountingDocumentItem,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlDocumentItemModel,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueMicroliter,
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_hires import constants
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_reader import (
    RocheCedexHiResReader,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none
from allotropy.parsers.vendor_parser import VendorParser

DataType = TypeVar("DataType")


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
    Datatype: The value from the specified cell converted to the specified datatype.
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


def get_calculated_data(
    dataframe: pd.DataFrame, column: str, row: int, datatype: Any
) -> Any:
    """
    Retrieves a value from a specified column and row in a DataFrame, converts it to a float
    by dividing it by 1,000,000, and then converts it to the specified datatype.

    Parameters:
    dataframe (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    row (int): The row index from which to retrieve the value.
    datatype (Any): The type to which the value should be further converted.

    Returns:
    Any: The value from the specified cell after conversion, or None if the value is not found.
    """
    value = get_value(dataframe, column, row)
    if value is not None:
        value = float(Decimal(str(value)) / Decimal("1000000"))
        return datatype(value=value)
    return value


def get_system_value(data: pd.DataFrame, column_name: str) -> str:
    """
    Retrieves the unique value from a specified column in a DataFrame, ensuring that there
    is only one unique value. If there are multiple unique values, raises an error.

    Parameters:
    data (pd.DataFrame): The DataFrame from which to retrieve the unique value.
    column_name (str): The name of the column from which to retrieve the unique value.

    Returns:
    str: The unique value from the specified column.

    Raises:
    AllotropeConversionError: If there are multiple unique values in the column.
    """
    unique_values = set(data[column_name])
    if len(unique_values) != 1:
        message = f"{constants.MULTIPLE_SYSTEM_ERROR} '{column_name}'"
        raise AllotropeConversionError(message)
    return str(next(iter(unique_values)))


class RocheCedexHiResParser(VendorParser):
    """
    A parser for Roche Cedex HiRes data files, converting them to Allotrope models.

    Properties:
    display_name (str): The display name of the parser.
    release_state (ReleaseState): The current release state of the parser.

    Methods:
    to_allotrope(named_file_contents: NamedFileContents) -> Model:
        Converts the named file contents to an Allotrope model.

    _get_model(data: pd.DataFrame, filename: str) -> Model:
        Constructs the Allotrope model from the parsed data.

    _get_device_system_document(data: pd.DataFrame) -> DeviceSystemDocument:
        Constructs the DeviceSystemDocument from the parsed data.

    _get_cell_counting_document(data: pd.DataFrame) -> list[CellCountingDocumentItem]:
        Constructs a list of CellCountingDocumentItems from the parsed data.

    _get_cell_counting_document_item(data: pd.DataFrame, row: int) -> CellCountingDocumentItem:
        Constructs a CellCountingDocumentItem for a specific row of data.
    """

    @property
    def display_name(self) -> str:
        """
        Returns the display name of the parser.

        Returns:
        str: The display name of the parser.
        """
        return constants.DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        """
        Returns the current release state of the parser.

        Returns:
        ReleaseState: The current release state of the parser.
        """
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        """
        Converts the named file contents to an Allotrope model.

        Parameters:
        named_file_contents (NamedFileContents): Contains the contents of instrument export file which is converted to ASM model.

        Returns:
        Model: The resulting Allotrope model.
        """
        return self._get_model(
            data=RocheCedexHiResReader.read(named_file_contents),
            filename=named_file_contents.original_file_name,
        )

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        """
        Constructs the Allotrope model from the parsed data.

        Parameters:
        data (pd.DataFrame): The parsed data.
        filename (str): The original file name.

        Returns:
        Model: The constructed Allotrope model.
        """
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=self._get_device_system_document(data),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=constants.CEDEX_SOFTWARE,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                cell_counting_document=self._get_cell_counting_document(data),
            ),
        )

    def _get_device_system_document(self, data: pd.DataFrame) -> DeviceSystemDocument:
        """
        Constructs the DeviceSystemDocument from the parsed data.

        Parameters:
        data (pd.DataFrame): The parsed data.

        Returns:
        DeviceSystemDocument: The constructed DeviceSystemDocument.
        """
        return DeviceSystemDocument(
            model_number=constants.MODEL_NUMBER,
            product_manufacturer=constants.PRODUCT_MANUFACTURER,
            asset_management_identifier=get_system_value(data, "System name"),
            description=get_system_value(data, "System description"),
            device_identifier=str(get_system_value(data, "Cedex ID")),
            brand_name=constants.BRAND_NAME,
        )

    def _get_cell_counting_document(
        self, data: pd.DataFrame
    ) -> list[CellCountingDocumentItem]:
        """
        Constructs a list of CellCountingDocumentItems from the parsed data.

        Parameters:
        data (pd.DataFrame): The parsed data.

        Returns:
        list[CellCountingDocumentItem]: A list of CellCountingDocumentItems.
        """
        return [
            self._get_cell_counting_document_item(data, i)
            for i in range(len(data.index))
        ]

    def _get_cell_counting_document_item(
        self, data: pd.DataFrame, row: int
    ) -> CellCountingDocumentItem:
        """
        Constructs a CellCountingDocumentItem for a specific row of data.

        Parameters:
        data (pd.DataFrame): The parsed data.
        row (int): The row index of the data.

        Returns:
        CellCountingDocumentItem: The constructed CellCountingDocumentItem.
        """
        sample_custom_document = {
            "group identifier": get_value(data, "Data set name", row),
            "sample draw time": self._get_date_time(
                str(get_value(data, "Sample draw Time", row))
            ),
        }
        processed_data_custom_document = {
            "average compactness": get_property_value(
                data, "Avg Compactness", row, TQuantityValueUnitless
            ),
            "average area": get_property_value(
                data, "Avg Area", row, TQuantityValueUnitless
            ),
            "average perimeter": get_property_value(
                data, "Avg Perimeter", row, TQuantityValueMicrometer
            ),
            "average segment area": get_property_value(
                data, "Avg Segm. Area", row, TQuantityValueUnitless
            ),
            "total object count": get_property_value(
                data, "Total Object Count", row, TQuantityValueCell
            ),
            "standard deviation": get_property_value(
                data, "Std Dev.", row, TQuantityValueCell
            ),
            "aggregate rate": get_property_value(
                data, "Aggregate Rate", row, TQuantityValuePercent
            ),
        }
        return CellCountingDocumentItem(
            analyst=get_value(data, "Username", row),
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_time=self._get_date_time(
                            str(get_value_not_none(data, "Date finished", row))
                        ),
                        measurement_identifier=random_uuid_str(),
                        sample_document=add_custom_information_document(
                            SampleDocument(
                                sample_identifier=get_value_not_none(
                                    data, "Sample identifer", row
                                ),
                                batch_identifier=get_value(
                                    data, "Reactor identifer", row
                                ),
                            ),
                            sample_custom_document,
                        ),
                        device_control_aggregate_document=CellCountingDetectorDeviceControlAggregateDocument(
                            device_control_document=[
                                DeviceControlDocumentItemModel(
                                    device_type=constants.DEVICE_TYPE,
                                    detection_type=constants.DETECTION_TYPE,
                                    sample_volume_setting=get_property_value(
                                        data,
                                        "Sample volume",
                                        row,
                                        TQuantityValueMicroliter,
                                    ),
                                )
                            ]
                        ),
                        processed_data_aggregate_document=ProcessedDataAggregateDocument(
                            processed_data_document=[
                                add_custom_information_document(
                                    ProcessedDataDocumentItem(
                                        data_processing_document=DataProcessingDocument(
                                            cell_type_processing_method=get_value(
                                                data, "Cell type name", row
                                            ),
                                            cell_density_dilution_factor=get_property_value(
                                                data,
                                                "Dilution",
                                                row,
                                                TQuantityValueUnitless,
                                            ),
                                        ),
                                        viability__cell_counter_=TQuantityValuePercent(
                                            value=get_value_not_none(
                                                data, "Viability", row
                                            )
                                        ),
                                        viable_cell_density__cell_counter_=assert_not_none(
                                            get_calculated_data(
                                                data,
                                                "Viable Cell Conc.",
                                                row,
                                                TQuantityValueMillionCellsPerMilliliter,
                                            ),
                                            name="Viable Cell Conc.",
                                        ),
                                        total_cell_density__cell_counter_=get_calculated_data(
                                            data,
                                            "Total Cell Conc.",
                                            row,
                                            TQuantityValueMillionCellsPerMilliliter,
                                        ),
                                        dead_cell_density__cell_counter_=get_calculated_data(
                                            data,
                                            "Dead Cell Conc.",
                                            row,
                                            TQuantityValueMillionCellsPerMilliliter,
                                        ),
                                        total_cell_count=get_property_value(
                                            data,
                                            "Total Cell Count",
                                            row,
                                            TQuantityValueCell,
                                        ),
                                        viable_cell_count=get_property_value(
                                            data,
                                            "Viable Cell Count",
                                            row,
                                            TQuantityValueCell,
                                        ),
                                        dead_cell_count=get_property_value(
                                            data,
                                            "Dead Cell Count",
                                            row,
                                            TQuantityValueCell,
                                        ),
                                        average_live_cell_diameter__cell_counter_=get_property_value(
                                            data,
                                            "Avg Diameter",
                                            row,
                                            TQuantityValueMicrometer,
                                        ),
                                    ),
                                    processed_data_custom_document,
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )

""" Parser file for Thermo Fisher Scientific Qubit FLex Parser"""

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SpectrophotometryAggregateDocument,
    SpectrophotometryDocumentItem,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
    FluorescencePointDetectionDeviceControlAggregateDocument, FluorescencePointDetectionDeviceControlDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrogramPerMicroliter,
    TQuantityValueMicrogramPerMilliliter,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilligramPerMilliliter,
    TQuantityValueNanogramPerMicroliter,
    TQuantityValueNanogramPerMilliliter,
    TQuantityValueNanometer,
    TQuantityValuePicogramPerMilliliter, TQuantityValueRelativeFluorescenceUnit, TQuantityValueMicroliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
    TQuantityValue,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_qubit_flex.qubit_flex_reader import (
    QubitFlexReader, constants
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none
from allotropy.parsers.vendor_parser import VendorParser

ConcentrationType = (
        TQuantityValueMicrogramPerMicroliter
        | TQuantityValueMicrogramPerMilliliter
        | TQuantityValueMilligramPerMilliliter
        | TQuantityValueNanogramPerMicroliter
        | TQuantityValueNanogramPerMilliliter
        | TQuantityValuePicogramPerMilliliter
)
ConcentrationClassType = (
        type[TQuantityValueMicrogramPerMicroliter]
        | type[TQuantityValueMicrogramPerMilliliter]
        | type[TQuantityValueMilligramPerMilliliter]
        | type[TQuantityValueNanogramPerMicroliter]
        | type[TQuantityValueNanogramPerMilliliter]
        | type[TQuantityValuePicogramPerMilliliter]
)

CONCENTRATION_UNIT_TO_TQUANTITY: Mapping[str, ConcentrationClassType] = {
    "ug/ul": TQuantityValueMicrogramPerMicroliter,
    "ug/ml": TQuantityValueMicrogramPerMilliliter,
    "mg/ml": TQuantityValueMilligramPerMilliliter,
    "ng/ul": TQuantityValueNanogramPerMicroliter,
    "ng/ml": TQuantityValueNanogramPerMilliliter,
    "pg/ul": TQuantityValuePicogramPerMilliliter,
}


def _get_str_or_none(data_frame: pd.DataFrame, row: int, column: str) -> str | None:
    if column not in data_frame.columns:
        return None

    val = data_frame.iloc[row][column]
    if pd.isna(val):
        return None

    return str(val)


def _get_str(data_frame: pd.DataFrame, row: int, column: str) -> str:
    val = _get_str_or_none(data_frame=data_frame, row=row, column=column)

    assert_not_none(val)

    return str(val)


def _get_value(data_frame: pd.DataFrame, column: str, row: int) -> Any | None:
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


def _get_property_value(
        data_frame: pd.DataFrame, column: str, row: int, datatype: Any
) -> Any:
    """
    Retrieves the value from a specified column and row in a DataFrame and converts it
    to the specified datatype.

    Parameters:
    data_frame (pd.DataFrame): The DataFrame from which to retrieve the value.
    column (str): The column name from which to retrieve the value.
    row (int): The row index from which to retrieve the value.
    datatype (Any): The type to which the retrieved value should be converted.

    Returns:
    Any: The value from the specified cell converted to the specified datatype.
         Returns None if the value is not found.
    """
    return (
        datatype(value=value) if (value := _get_value(data_frame, column, row)) else None
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


def _get_float(data_frame: pd.DataFrame, row: int, column: str) -> JsonFloat:
    try:
        return float(data_frame.iloc[row][column])
    except (ValueError, TypeError):
        return InvalidJsonFloat.NaN


class QubitFlexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Thermo Fisher NanoDrop Eight"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        return self._get_model(
            data=QubitFlexReader.read(named_file_contents),
            filename=named_file_contents.original_file_name,
        )

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                spectrophotometry_document=self._get_spectrophotometry_document(data),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=constants.SOFTWARE_NAME,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION
                ),
                device_system_document=DeviceSystemDocument(
                    model_number=constants.MODEL_NUMBER,
                    device_identifier="N/A",
                    brand_name=constants.BRAND_NAME,
                    product_manufacturer=constants.PRODUCT_MANUFACTURER
                ),
            ),
        )

    def _get_spectrophotometry_document(
            self, data: pd.DataFrame
    ) -> list[SpectrophotometryDocumentItem]:
        return [
            SpectrophotometryDocumentItem(
                measurement_aggregate_document=self._get_measurement_aggregate_doctment(data, i))
            for i in range(len(data.index))
        ]

    def _get_measurement_aggregate_document(self, data, i) -> MeasurementAggregateDocument:
        measurement_custom_document = {"reagent lot number": _get_value(data, "Reagent Lot#", i),
                                       "calibrated tubes": _get_value(data, "Calibrated Tubes", i)}
        return add_custom_information_document(
            MeasurementAggregateDocument(measurement_time=self._get_date_time(str(_get_value(data, "Test Date", i))),
                                         experiment_type=_get_value(data, "Assay Name", i),
                                         container_type=constants.CONTAINER_TYPE,
                                         measurement_document=self._get_measurement_document(data, i)),
            measurement_custom_document)

    def _get_measurement_document(self, data, i) -> list[FluorescencePointDetectionMeasurementDocumentItems]:
        return [FluorescencePointDetectionMeasurementDocumentItems(fluorescence=self._get_fluorescence_value(data, i),
                                                                   measurement_identifier=random_uuid_str(),
                                                                   sample_document=self._get_sample_document(data, i),
                                                                   device_control_aggregate_document=self._get_device_control_document(
                                                                       data, i))]

    def _get_fluorescence_value(self, data, i) -> TQuantityValueRelativeFluorescenceUnit:
        value = _get_property_value(data, "Sample RFU", i, TQuantityValueRelativeFluorescenceUnit)
        return value

    def _get_sample_document(self, data, i) -> SampleDocument:
        sample_id = _get_value(data, "Sample ID", i)
        location_id = _get_value(data, "well", i)
        well_plate_id = _get_value(data, "plate barcode", i)
        if sample_id is None:
            sample_id = _get_property_value(data, "Sample Name", i)
        sample_custom_document = {"original sample concentration": _get_property_value(data, "Original Sample Conc.", i,
                                                                                       CONCENTRATION_UNIT_TO_TQUANTITY[
                                                                                           _get_value(data,
                                                                                                      "Original sample conc. units",
                                                                                                      i)]),
                                  "qubit tube concentration": _get_property_value(data, "Qubit Tube Conc.", i,
                                                                                  CONCENTRATION_UNIT_TO_TQUANTITY[
                                                                                      _get_value(data,
                                                                                                 "Qubit tube conc. units",
                                                                                                 i)]),
                                  "standard 1 concentration": _get_property_value(data, "Std 1 RFU", i,
                                                                                  TQuantityValueRelativeFluorescenceUnit),
                                  "standard 2 concentration": _get_property_value(data, "Std 2 RFU", i,
                                                                                  TQuantityValueRelativeFluorescenceUnit),
                                  "standard 3 concentration": _get_property_value(data, "Std 3 RFU", i,
                                                                                  TQuantityValueRelativeFluorescenceUnit)}
        return add_custom_information_document(
            SampleDocument(sample_identifier=sample_id,
                           batch_identifier=str(_get_value(data, "Run ID", i)),
                           location_identifier=location_id,
                           well_plate_identifier=well_plate_id), sample_custom_document)

    def _get_device_control_document(self, data, i) -> FluorescencePointDetectionDeviceControlAggregateDocument:
        custom_device_document = {
            "sample volume setting": _get_property_value(data, "Sample Volume (uL)", i, TQuantityValueMicroliter),
            "operating minimum": _get_property_value(data, "Extended Low Range", i,
                                                     TQuantityValueNanogramPerMicroliter),
            "operating range": _get_property_value(data, "Core Range", i, TQuantityValueNanogramPerMicroliter),
            "operating maximum": _get_property_value(data, "Extended High Range", i,
                                                     TQuantityValueNanogramPerMicroliter),
            "excitation setting": _get_value(data, "Excitation", i),
            "dilution factor": _get_property_value(data, "Dilution Factor", i, TQuantityValueUnitless)}
        return add_custom_information_document(FluorescencePointDetectionDeviceControlAggregateDocument(
            device_control_document=[
                FluorescencePointDetectionDeviceControlDocumentItem(device_type=constants.DEVICE_TYPE)]),
            custom_device_document)

from typing import Optional, TypeVar
import uuid

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrogramPerMicroliter,
    TQuantityValueMicrogramPerMilliliter,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilligramPerMilliliter,
    TQuantityValueNanogramPerMicroliter,
    TQuantityValueNanogramPerMilliliter,
    TQuantityValueNanometer,
    TQuantityValuePicogramPerMilliliter,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TQuantityValue,
    ValueEnum,
)
from allotropy.allotrope.models.spectrophotometry_benchling_2023_12_spectrophotometry import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument1,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    Model,
    SampleDocument,
    SpectrophotometryAggregateDocument,
    SpectrophotometryDocumentItem,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_reader import (
    NanoDropEightReader,
)
from allotropy.parsers.vendor_parser import VendorParser

T = TypeVar("T")

CONCENTRATION_UNIT_TO_TQUANTITY = {
    "ug/ul": TQuantityValueMicrogramPerMicroliter,
    "ug/ml": TQuantityValueMicrogramPerMilliliter,
    "mg/ml": TQuantityValueMilligramPerMilliliter,
    "ng/ul": TQuantityValueNanogramPerMicroliter,
    "ng/ml": TQuantityValueNanogramPerMilliliter,
    "pg/ul": TQuantityValuePicogramPerMilliliter,
}


def _get_str(data_frame: pd.DataFrame, row: int, column: str) -> Optional[str]:
    if column not in data_frame.columns:
        return None
    if pd.isna(data_frame.iloc[row][column]):
        return None

    return str(data_frame.iloc[row][column])


def _get_float(data_frame: pd.DataFrame, row: int, column: str) -> float | ValueEnum:
    try:
        return float(data_frame.iloc[row][column])
    except (ValueError, TypeError):
        return ValueEnum.NaN


def _get_concentration(conc: float | ValueEnum, unit: Optional[str]) -> Optional[T]:
    if unit in CONCENTRATION_UNIT_TO_TQUANTITY and isinstance(conc, float):
        cls = CONCENTRATION_UNIT_TO_TQUANTITY[unit]
        return cls(value=conc)  # type: ignore[return-value]

    return None


class NanodropEightParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents, filename = named_file_contents
        data = NanoDropEightReader.read(contents)
        data = self._add_measurement_uuids(data)
        return self._get_model(data, filename)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                spectrophotometry_document=self._get_spectrophotometry_document(data),
                calculated_data_aggregate_document=CalculatedDataAggregateDocument(
                    calculated_data_document=self._get_calculated_data_document(data),
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    model_number="Nanodrop Eight",
                    device_identifier="Nanodrop",
                ),
            ),
        )

    def _add_measurement_uuids(self, data: pd.DataFrame) -> pd.DataFrame:
        data["A260 uuid"] = [str(uuid.uuid4()) for _ in range(len(data.index))]
        data["A280 uuid"] = [str(uuid.uuid4()) for _ in range(len(data.index))]
        return data

    def _get_spectrophotometry_document(
        self, data: pd.DataFrame
    ) -> list[SpectrophotometryDocumentItem]:
        return [
            self._get_spectrophotometry_document_item(data, i)
            for i in range(len(data.index))
        ]

    def _get_calculated_data_document(
        self, data: pd.DataFrame
    ) -> list[CalculatedDataDocumentItem]:
        calculated_data_documents = []
        for i in range(len(data.index)):
            if _get_str(data, i, "260/280"):
                calculated_data_documents.append(self._get_260_280(data, i))

            if _get_str(data, i, "260/230"):
                calculated_data_documents.append(self._get_260_230(data, i))

        return calculated_data_documents

    def _get_260_280(self, data: pd.DataFrame, row: int) -> CalculatedDataDocumentItem:

        return CalculatedDataDocumentItem(
            calculated_data_name="A260/280",
            calculated_result=TQuantityValue(
                value=_get_float(data, row, "260/280"), unit="unitless"
            ),
            calculated_data_identifier=str(uuid.uuid4()),
            data_source_aggregate_document=DataSourceAggregateDocument1(
                [
                    DataSourceDocumentItem(
                        data_source_feature="absorbance",
                        data_source_identifier=str(_get_str(data, row, "A260 uuid")),
                    ),
                    DataSourceDocumentItem(
                        data_source_feature="absorbance",
                        data_source_identifier=str(_get_str(data, row, "A280 uuid")),
                    ),
                ]
            ),
        )

    def _get_260_230(self, data: pd.DataFrame, row: int) -> CalculatedDataDocumentItem:
        return CalculatedDataDocumentItem(
            calculated_data_name="A260/230",
            calculated_result=TQuantityValue(
                value=_get_float(data, row, "260/230"), unit="unitless"
            ),
            calculated_data_identifier=str(uuid.uuid4()),
            data_source_aggregate_document=DataSourceAggregateDocument1(
                [
                    DataSourceDocumentItem(
                        data_source_feature="absorbance",
                        data_source_identifier=str(_get_str(data, row, "A260 uuid")),
                    )
                ]
            ),
        )

    def _get_spectrophotometry_document_item(
        self, data: pd.DataFrame, row: int
    ) -> SpectrophotometryDocumentItem:
        return SpectrophotometryDocumentItem(
            analyst=_get_str(data, row, "User ID"),
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(
                    str(_get_str(data, row, "Date"))
                    + " "
                    + str(_get_str(data, row, "Time"))
                ),
                experiment_type=_get_str(data, row, "NA Type"),
                measurement_document=self._get_measurement_document(data=data, row=row),
            ),
        )

    def _get_measurement_document(
        self, data: pd.DataFrame, row: int
    ) -> list[UltravioletAbsorbancePointDetectionMeasurementDocumentItems]:
        measurement_docs = []
        if _get_str(data, row, "A260"):
            measurement_docs.append(
                UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                    measurement_identifier=str(_get_str(data, row, "A260 uuid")),
                    sample_document=SampleDocument(
                        sample_identifier=str(_get_str(data, row, "Sample ID")),
                        well_plate_identifier=_get_str(data, row, "Plate ID"),
                        location_identifier=_get_str(data, row, "Well"),
                    ),
                    # capture concentration on the A260 measurement document if the experiment type is
                    # DNA or RNA, protein and other concentration is captured on A280 measurment
                    mass_concentration=_get_concentration(
                        _get_float(data, row, str(self._get_concentration_col(data))),
                        _get_str(data, row, "Units"),
                    )
                    if "NA" in str(_get_str(data, row, "NA Type"))
                    and self._get_concentration_col(data)
                    else None,
                    device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                        device_control_document=[
                            UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                                device_type="absorbance detector",
                                detector_wavelength_setting=TQuantityValueNanometer(
                                    value=260
                                ),
                            )
                        ]
                    ),
                    absorbance=TQuantityValueMilliAbsorbanceUnit(
                        _get_float(data, row, "A260")
                    ),
                )
            )
        a280_col = "A280"
        if a280_col not in data.columns and "A280 10mm" in data.columns:
            a280_col = "A280 10mm"
        if _get_str(data, row, a280_col):
            measurement_docs.append(
                UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                    measurement_identifier=str(_get_str(data, row, "A280 uuid")),
                    sample_document=SampleDocument(
                        sample_identifier=str(_get_str(data, row, "Sample ID")),
                        well_plate_identifier=_get_str(data, row, "Plate ID"),
                        location_identifier=_get_str(data, row, "Well"),
                    ),
                    # capture concentration on the A280 measurement document if the experiment type is
                    # something other than DNA or RNA
                    mass_concentration=_get_concentration(
                        _get_float(data, row, str(self._get_concentration_col(data))),
                        _get_str(data, row, "Units"),
                    )
                    if "NA" not in str(_get_str(data, row, "NA Type"))
                    and self._get_concentration_col(data)
                    else None,
                    device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                        device_control_document=[
                            UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                                device_type="absorbance detector",
                                detector_wavelength_setting=TQuantityValueNanometer(
                                    value=280
                                ),
                            )
                        ]
                    ),
                    absorbance=TQuantityValueMilliAbsorbanceUnit(
                        _get_float(data, row, a280_col)
                    ),
                )
            )

        return measurement_docs

    def _get_concentration_col(self, data: pd.DataFrame) -> Optional[str]:
        for col in data.columns:
            if col.lower() in ["conc.", "conc", "concentration"]:
                return col
        return None

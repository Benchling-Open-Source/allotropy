from collections.abc import Mapping

import pandas as pd

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
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrogramPerMicroliter,
    TQuantityValueMicrogramPerMilliliter,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilligramPerMilliliter,
    TQuantityValueNanogramPerMicroliter,
    TQuantityValueNanogramPerMilliliter,
    TQuantityValueNanometer,
    TQuantityValuePicogramPerMilliliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_reader import (
    NanoDropEightReader,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_from_series,
    try_float_from_series_or_nan,
    try_str_from_series,
    try_str_from_series_or_none,
)
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


def _get_concentration(conc: JsonFloat, unit: str | None) -> ConcentrationType | None:
    if unit and unit in CONCENTRATION_UNIT_TO_TQUANTITY and isinstance(conc, float):
        cls = CONCENTRATION_UNIT_TO_TQUANTITY[unit]
        return cls(value=conc)

    return None


class NanodropEightParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Thermo Fisher NanoDrop Eight"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = NanoDropEightReader.read(named_file_contents)
        data = self._add_measurement_uuids(data)
        data.columns = data.columns.str.lower()
        return self._get_model(data, named_file_contents.original_file_name)

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
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    model_number="Nanodrop Eight",
                    device_identifier="Nanodrop",
                ),
            ),
        )

    def _add_measurement_uuids(self, data: pd.DataFrame) -> pd.DataFrame:
        data["a260 uuid"] = [random_uuid_str() for _ in range(len(data.index))]
        data["a280 uuid"] = [random_uuid_str() for _ in range(len(data.index))]
        return data

    def _get_spectrophotometry_document(
        self, data: pd.DataFrame
    ) -> list[SpectrophotometryDocumentItem]:
        return list(data.apply(self._get_spectrophotometry_document_item, axis=1))

    def _get_calculated_data_document(
        self, data: pd.DataFrame
    ) -> list[CalculatedDataDocumentItem]:
        cal_docs = []

        def get_cal_docs(row_data):
            if try_str_from_series_or_none(row_data, "260/280"):
                cal_docs.append(self._get_260_280(row_data))

            if try_str_from_series_or_none(row_data, "260/230"):
                cal_docs.append(self._get_260_230(row_data))

        data.apply(get_cal_docs, axis=1)
        return cal_docs

    def _get_260_280(self, row_data: pd.Series) -> CalculatedDataDocumentItem:
        data_source_doc_items = []
        if try_str_from_series_or_none(row_data, "a260"):
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=try_str_from_series(row_data, "a260 uuid"),
                )
            )

        if try_str_from_series_or_none(row_data, "a280") or try_str_from_series_or_none(row_data, "a280 10mm"):
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=try_str_from_series(row_data, "a280 uuid"),
                )
            )

        data_source_aggregate_document = None
        if data_source_doc_items:
            data_source_aggregate_document = DataSourceAggregateDocument(
                data_source_document=data_source_doc_items
            )

        return CalculatedDataDocumentItem(
            calculated_data_name="A260/280",
            calculated_result=TQuantityValueUnitless(
                value=try_float_from_series(row_data, "260/280")
            ),
            calculated_data_identifier=random_uuid_str(),
            data_source_aggregate_document=data_source_aggregate_document,
        )

    def _get_260_230(self, row_data: pd.Series) -> CalculatedDataDocumentItem:
        data_source_doc_items = []
        if try_str_from_series_or_none(row_data, "a260"):
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=try_str_from_series(row_data, "a260 uuid"),
                )
            )

        data_source_aggregate_document = None
        if data_source_doc_items:
            data_source_aggregate_document = DataSourceAggregateDocument(
                data_source_document=data_source_doc_items
            )
        return CalculatedDataDocumentItem(
            calculated_data_name="A260/230",
            calculated_result=TQuantityValueUnitless(
                value=try_float_from_series(row_data, "260/230")
            ),
            calculated_data_identifier=random_uuid_str(),
            data_source_aggregate_document=data_source_aggregate_document,
        )

    def _get_spectrophotometry_document_item(
        self, row_data: pd.Series
    ) -> SpectrophotometryDocumentItem:
        return SpectrophotometryDocumentItem(
            analyst=try_str_from_series_or_none(row_data, "user id"),
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(
                    try_str_from_series_or_none(row_data, "date") + " " + try_str_from_series_or_none(row_data, "time")
                ),
                experiment_type=try_str_from_series_or_none(row_data, "na type"),
                measurement_document=self._get_measurement_documents(row_data),
            ),
        )

    def _get_measurement_document(
        self,
        row_data: pd.Series,
        concentration_col: str | None,
        absorbance_col: str,
        wavelength: int,
        uuid_col: str,
    ):
        mass_concentration = None
        if concentration_col:
            mass_concentration = _get_concentration(
                try_float_from_series(row_data, concentration_col),
                try_str_from_series_or_none(row_data, "units"),
            )

        processed_data_aggregate_document = None
        if mass_concentration is not None:
            processed_data_aggregate_document = ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(mass_concentration=mass_concentration)
                ]
            )

        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=try_str_from_series_or_none(row_data, uuid_col),
            sample_document=SampleDocument(
                sample_identifier=try_str_from_series(row_data, "sample id")
                if try_str_from_series_or_none(row_data, "sample id")
                else NOT_APPLICABLE,
                well_plate_identifier=try_str_from_series_or_none(row_data, "plate id"),
                location_identifier=try_str_from_series_or_none(row_data, "well"),
            ),
            processed_data_aggregate_document=processed_data_aggregate_document,
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="absorbance detector",
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=wavelength
                        ),
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=try_float_from_series(row_data, absorbance_col)
            ),
        )

    def _get_measurement_documents(
        self, row_data: pd.Series
    ) -> list[
        FluorescencePointDetectionMeasurementDocumentItems
        | UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    ]:
        measurement_docs: list[
            FluorescencePointDetectionMeasurementDocumentItems
            | UltravioletAbsorbancePointDetectionMeasurementDocumentItems
        ]
        measurement_docs = []
        experiment_type = try_str_from_series_or_none(row_data, "na type")
        is_na_experiment = experiment_type and "NA" in experiment_type
        concentration_col = self._get_concentration_col(row_data)
        a280_col = "a280"
        if a280_col not in row_data.index and "a280 10mm" in row_data.index:
            a280_col = "a280 10mm"

        if try_str_from_series_or_none(row_data, "a260"):
            # capture concentration on the A260 measurement document if the experiment type is
            # DNA or RNA, protein and other concentration is captured on A280 measurment
            # if there is no experiment type and no 280 column add the concentration here
            capture_concentration = (
                is_na_experiment
                or not (experiment_type or a280_col in row_data.index)
            )
            measurement_docs.append(self._get_measurement_document(
                row_data,
                concentration_col if capture_concentration else None,
                "a260",
                260,
                "a260 uuid",
            ))

        if try_str_from_series_or_none(row_data, a280_col):
            # capture concentration on the A280 measurement document if the experiment type is
            # something other than DNA or RNA or if the experiment type is not specified
            capture_concentration = not (experiment_type and is_na_experiment)
            measurement_docs.append(self._get_measurement_document(
                row_data,
                concentration_col if capture_concentration else None,
                a280_col,
                280,
                "a280 uuid",
            ))

        return measurement_docs

    def _get_concentration_col(self, row_data: pd.Series) -> str | None:
        # TODO: reverse this
        for col in row_data.index:
            if col.lower() in ["conc.", "conc", "concentration"]:
                return col
        return None

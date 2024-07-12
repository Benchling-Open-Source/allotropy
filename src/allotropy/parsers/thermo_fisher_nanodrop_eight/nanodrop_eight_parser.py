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
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_structure import (
    SpectroscopyMeasurement,
    SpectroscopyRow,
    SpectroscopyRows,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


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
        return self._get_model(data, named_file_contents.original_file_name)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        rows = SpectroscopyRows.create(data)
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                spectrophotometry_document=[self._get_spectrophotometry_document_item(row) for row in rows.rows],
                calculated_data_aggregate_document=CalculatedDataAggregateDocument(
                    calculated_data_document=self._get_calculated_data_document(rows),
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

    def _get_calculated_data_document(
        self, rows: SpectroscopyRows
    ) -> list[CalculatedDataDocumentItem]:
        cal_docs = []

        for row in rows.rows:
            if row.a260_280:
                cal_docs.append(self._get_260_280(row))

            if row.a260_230:
                cal_docs.append(self._get_260_230(row))

        return cal_docs

    def _get_260_280(self, row: SpectroscopyRow) -> CalculatedDataDocumentItem:
        data_source_doc_items = []

        measurement = row.measurements.get(260)
        if measurement:
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=measurement.uuid,
                )
            )

        measurement = row.measurements.get(280)
        if measurement:
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=measurement.uuid,
                )
            )

        data_source_aggregate_document = None
        if data_source_doc_items:
            data_source_aggregate_document = DataSourceAggregateDocument(
                data_source_document=data_source_doc_items
            )

        return CalculatedDataDocumentItem(
            calculated_data_name="A260/280",
            calculated_result=TQuantityValueUnitless(value=row.a260_280),
            calculated_data_identifier=random_uuid_str(),
            data_source_aggregate_document=data_source_aggregate_document,
        )

    def _get_260_230(self, row: SpectroscopyRow) -> CalculatedDataDocumentItem:
        measurement = row.measurements.get(260)
        data_source_doc_items = []
        if measurement:
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=measurement.uuid,
                )
            )

        data_source_aggregate_document = None
        if data_source_doc_items:
            data_source_aggregate_document = DataSourceAggregateDocument(
                data_source_document=data_source_doc_items
            )
        return CalculatedDataDocumentItem(
            calculated_data_name="A260/230",
            calculated_result=TQuantityValueUnitless(value=row.a260_230),
            calculated_data_identifier=random_uuid_str(),
            data_source_aggregate_document=data_source_aggregate_document,
        )

    def _get_spectrophotometry_document_item(
        self, row: SpectroscopyRow
    ) -> SpectrophotometryDocumentItem:
        return SpectrophotometryDocumentItem(
            analyst=row.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(row.timestamp),
                experiment_type=row.experiment_type,
                measurement_document=[self._get_measurement_document(measurement) for measurement in row.measurements.values()],
            ),
        )

    def _get_measurement_document(self, measurement: SpectroscopyMeasurement):
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.uuid,
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
                location_identifier=measurement.location_identifier,
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(mass_concentration=measurement.mass_concentration)
                ]
            ) if measurement.mass_concentration else None,
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="absorbance detector",
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=measurement.wavelength,
                        ),
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=measurement.absorbance
            ),
        )

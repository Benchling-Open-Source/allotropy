from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
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
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_reader import (
    NanoDropEightReader,
)
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_structure import (
    SpectroscopyMeasurement,
    SpectroscopyRow,
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
        rows = SpectroscopyRow.create_rows(data)
        return self._get_model(rows, named_file_contents.original_file_name)

    def _get_model(self, rows: list[SpectroscopyRow], filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                spectrophotometry_document=[
                    self._get_spectrophotometry_document_item(row) for row in rows
                ],
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

    def _get_calculated_data_document(
        self, rows: list[SpectroscopyRow]
    ) -> list[CalculatedDataDocumentItem]:
        cal_docs = []

        for row in rows:
            cal_docs.append(self._get_260_280(row))
            cal_docs.append(self._get_260_230(row))

        return [doc for doc in cal_docs if doc]

    def _get_260_280(self, row: SpectroscopyRow) -> CalculatedDataDocumentItem | None:
        if not row.a260_280:
            return None
        data_source_doc_items = []

        measurement = row.measurements.get(260)
        if measurement:
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=measurement.measurement_id,
                )
            )

        measurement = row.measurements.get(280)
        if measurement:
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=measurement.measurement_id,
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

    def _get_260_230(self, row: SpectroscopyRow) -> CalculatedDataDocumentItem | None:
        if not row.a260_230:
            return None

        measurement = row.measurements.get(260)
        data_source_doc_items = []
        if measurement:
            data_source_doc_items.append(
                DataSourceDocumentItem(
                    data_source_feature="absorbance",
                    data_source_identifier=measurement.measurement_id,
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
                measurement_document=[
                    self._get_measurement_document(measurement)
                    for measurement in row.measurements.values()
                ],
            ),
        )

    def _get_measurement_document(
        self, measurement: SpectroscopyMeasurement
    ) -> UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.measurement_id,
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
                location_identifier=measurement.location_identifier,
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        mass_concentration=measurement.mass_concentration
                    )
                ]
            )
            if measurement.mass_concentration
            else None,
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
            absorbance=TQuantityValueMilliAbsorbanceUnit(value=measurement.absorbance),
        )

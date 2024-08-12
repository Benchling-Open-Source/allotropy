from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    CalibrationAggregateDocument,
    CalibrationDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    MultiAnalyteProfilingAggregateDocument,
    MultiAnalyteProfilingDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Data,
    Error,
    Measurement,
    Metadata,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    create_data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class LuminexXponentParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Luminex xPONENT"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = create_data(reader, named_file_contents.original_file_name)
        return self._get_model(data)

    def _get_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/multi-analyte-profiling/BENCHLING/2024/01/multi-analyte-profiling.manifest",
            multi_analyte_profiling_aggregate_document=MultiAnalyteProfilingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    calibration_aggregate_document=CalibrationAggregateDocument(
                        calibration_document=[
                            CalibrationDocumentItem(
                                calibration_name=calibration.name,
                                calibration_report=calibration.report,
                                calibration_time=self._get_date_time(calibration.time),
                            )
                            for calibration in data.metadata.calibrations
                        ]
                    ),
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                multi_analyte_profiling_document=[
                    MultiAnalyteProfilingDocumentItem(
                        analyst=data.metadata.analyst,
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            analytical_method_identifier=data.metadata.analytical_method_identifier,
                            method_version=data.metadata.method_version,
                            experimental_data_identifier=data.metadata.experimental_data_identifier,
                            container_type=data.metadata.container_type,
                            plate_well_count=TQuantityValueNumber(
                                value=data.metadata.plate_well_count
                            ),
                            measurement_document=[
                                self._get_measurement_document_item(
                                    group.measurements[0],
                                    data.metadata,
                                )
                            ],
                        ),
                    )
                    for group in data.measurement_groups
                ],
            ),
        )

    def _get_measurement_document_item(
        self,
        measurement: Measurement,
        metadata: Metadata,
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self._get_date_time(measurement.measurement_time),
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                location_identifier=measurement.location_identifier,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        sample_volume_setting=TQuantityValueMicroliter(
                            value=metadata.sample_volume_setting
                        ),
                        dilution_factor_setting=TQuantityValueUnitless(
                            value=measurement.dilution_factor_setting
                        ),
                        detector_gain_setting=metadata.detector_gain_setting,
                        minimum_assay_bead_count_setting=TQuantityValueNumber(
                            value=metadata.minimum_bead_count_setting
                        ),
                    )
                ]
            ),
            assay_bead_count=TQuantityValueNumber(value=measurement.assay_bead_count),
            analyte_aggregate_document=AnalyteAggregateDocument(
                analyte_document=[
                    AnalyteDocumentItem(
                        analyte_identifier=analyte.identifier,
                        analyte_name=analyte.name,
                        assay_bead_identifier=analyte.assay_bead_identifier,
                        assay_bead_count=TQuantityValueNumber(
                            value=analyte.assay_bead_count
                        ),
                        fluorescence=TQuantityValueRelativeFluorescenceUnit(
                            value=analyte.fluorescence,
                            has_statistic_datum_role=TStatisticDatumRole.median_role,
                        ),
                    )
                    for analyte in measurement.analytes
                ]
            ),
            error_aggregate_document=self._get_error_aggregate_document(measurement.errors),
        )

    def _get_error_aggregate_document(
        self, errors: list[Error] | None
    ) -> ErrorAggregateDocument | None:
        if not errors:
            return None

        return ErrorAggregateDocument(
            error_document=[
                ErrorDocumentItem(error=error.error, error_feature=error.feature)
                for error in errors
            ]
        )

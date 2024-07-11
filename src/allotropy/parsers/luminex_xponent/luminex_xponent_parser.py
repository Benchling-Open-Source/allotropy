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
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    Data,
    Header,
    Measurement,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

DEFAULT_SOFTWARE_NAME = "xPONENT"
DEFAULT_CONTAINER_TYPE = "well plate"
DEFAULT_DEVICE_TYPE = "multi analyte profiling analyzer"


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
        data = Data.create(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: Data) -> Model:
        header = data.header
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/multi-analyte-profiling/BENCHLING/2024/01/multi-analyte-profiling.manifest",
            multi_analyte_profiling_aggregate_document=MultiAnalyteProfilingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=header.model_number,
                    equipment_serial_number=header.equipment_serial_number,
                    calibration_aggregate_document=CalibrationAggregateDocument(
                        calibration_document=[
                            CalibrationDocumentItem(
                                calibration_name=calibration_item.name,
                                calibration_report=calibration_item.report,
                                calibration_time=self._get_date_time(
                                    calibration_item.time
                                ),
                            )
                            for calibration_item in data.calibration_data
                        ]
                    ),
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=header.data_system_instance_identifier,
                    file_name=file_name,
                    software_name=DEFAULT_SOFTWARE_NAME,
                    software_version=header.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                multi_analyte_profiling_document=[
                    MultiAnalyteProfilingDocumentItem(
                        analyst=header.analyst,
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            analytical_method_identifier=header.analytical_method_identifier,
                            method_version=header.method_version,
                            experimental_data_identifier=header.experimental_data_identifier,
                            container_type=DEFAULT_CONTAINER_TYPE,
                            plate_well_count=TQuantityValueNumber(
                                value=header.plate_well_count
                            ),
                            measurement_document=[
                                self._get_measurement_document_item(
                                    measurement,
                                    header,
                                    data.minimum_bead_count_setting,
                                )
                            ],
                        ),
                    )
                    for measurement in data.measurement_list.measurements
                ],
            ),
        )

    def _get_measurement_document_item(
        self,
        measurement: Measurement,
        header_data: Header,
        minimum_bead_count_setting: float,
    ) -> MeasurementDocumentItem:
        error_aggregate_document = None
        if measurement.errors:
            error_aggregate_document = ErrorAggregateDocument(
                error_document=[
                    ErrorDocumentItem(error=error) for error in measurement.errors
                ]
            )

        return MeasurementDocumentItem(
            measurement_identifier=random_uuid_str(),
            measurement_time=self._get_date_time(header_data.measurement_time),
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                location_identifier=measurement.location_identifier,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=DEFAULT_DEVICE_TYPE,
                        sample_volume_setting=TQuantityValueMicroliter(
                            value=header_data.sample_volume_setting
                        ),
                        dilution_factor_setting=TQuantityValueUnitless(
                            value=measurement.dilution_factor_setting
                        ),
                        detector_gain_setting=header_data.detector_gain_setting,
                        minimum_assay_bead_count_setting=TQuantityValueNumber(
                            value=minimum_bead_count_setting
                        ),
                    )
                ]
            ),
            assay_bead_count=TQuantityValueNumber(value=measurement.assay_bead_count),
            analyte_aggregate_document=AnalyteAggregateDocument(
                analyte_document=[
                    AnalyteDocumentItem(
                        analyte_identifier=random_uuid_str(),
                        analyte_name=analyte.analyte_name,
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
            error_aggregate_document=error_aggregate_document,
        )

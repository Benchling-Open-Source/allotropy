from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
    SolutionAnalyzerDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueGramPerLiter,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilliliterPerLiter,
    TQuantityValueMillimolePerLiter,
)
from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Analyte,
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_bioht.constants import (
    OPTICAL_DENSITY,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import (
    create_data,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class RocheCedexBiohtParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Roche Cedex BioHT"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = create_data(named_file_contents)
        return self._get_model(data)

    def _get_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest",
            solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
                solution_analyzer_document=self._get_solution_analyzer_document(data),
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    device_identifier=NOT_APPLICABLE,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    UNC_path="",
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
            ),
        )

    def _get_solution_analyzer_document(
        self, data: Data
    ) -> list[SolutionAnalyzerDocumentItem]:
        solution_analyzer_document = []
        for measurement_group in data.measurement_groups:
            if not measurement_group.measurements:
                continue
            solution_analyzer_document.append(
                SolutionAnalyzerDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_document=[self._create_measurements(measurement, data.metadata) for measurement in measurement_group.measurements],
                        data_processing_time=self._get_date_time(measurement_group.data_processing_time),
                    ),
                    analyst=measurement_group.analyst,
                )
            )

        return solution_analyzer_document

    def _create_measurements(
        self,
        measurement: Measurement,
        metadata: Metadata
    ) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            measurement_time=self._get_date_time(measurement.measurement_time),
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                batch_identifier=measurement.batch_identifier,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[DeviceControlDocumentItem(device_type=metadata.device_type)]
            ),
            absorbance=quantity_or_none(TQuantityValueMilliAbsorbanceUnit, measurement.absorbance),
            analyte_aggregate_document=AnalyteAggregateDocument(analyte_document=[self._create_analyte_document(analyte) for analyte in measurement.analytes]) if measurement.analytes else None
        )

    def _create_analyte_document(self, analyte: Analyte) -> AnalyteDocument:
        if analyte.unit == "g/L":
            return AnalyteDocument(
                analyte_name=analyte.name,
                mass_concentration=TQuantityValueGramPerLiter(value=analyte.value),
            )
        elif analyte.unit == "mL/L":
            return AnalyteDocument(
                analyte_name=analyte.name,
                volume_concentration=TQuantityValueMilliliterPerLiter(value=analyte.value),
            )
        elif analyte.unit == "mmol/L":
            return AnalyteDocument(
                analyte_name=analyte.name,
                molar_concentration=TQuantityValueMillimolePerLiter(value=analyte.value),
            )
        elif analyte.unit == "U/L":
            if analyte.name == "ldh":
                return AnalyteDocument(
                    analyte_name=analyte.name,
                    molar_concentration=TQuantityValueMillimolePerLiter(
                        value=analyte.value * 0.0167 if analyte.value > 0 else analyte.value
                    ),
                )
            else:
                msg = f"Invalid unit for {analyte.name}: {analyte.unit}"
                raise AllotropeConversionError(msg)

        msg = f"Invalid unit for analyte: {analyte.unit}, value values are: g/L, mL/L, mmol/L"
        raise AllotropeConversionError(msg)

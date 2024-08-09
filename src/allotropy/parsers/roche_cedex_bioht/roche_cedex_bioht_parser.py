from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
    SolutionAnalyzerDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimolePerLiter,
)
from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_bioht.constants import (
    OPTICAL_DENSITY,
    SOLUTION_ANALYZER,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_reader import (
    RocheCedexBiohtReader,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import (
    Data,
    Measurement,
    Sample,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class RocheCedexBiohtParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Roche Cedex BioHT"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        reader = RocheCedexBiohtReader(contents)
        return self._get_model(
            Data.create(reader), named_file_contents.original_file_name
        )

    def _get_model(self, data: Data, file_name: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest",
            solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
                solution_analyzer_document=self._get_solution_analyzer_document(data),
                device_system_document=DeviceSystemDocument(
                    model_number=data.title.model_number,
                    equipment_serial_number=data.title.device_serial_number,
                    device_identifier=NOT_APPLICABLE,
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    UNC_path="",
                    software_name=data.title.model_number,
                    software_version=data.title.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
            ),
        )

    def _get_solution_analyzer_document(
        self, data: Data
    ) -> list[SolutionAnalyzerDocumentItem]:
        solution_analyzer_document = []
        for sample in data.samples:
            if docs := self._get_measurement_document(sample):
                solution_analyzer_document.append(
                    SolutionAnalyzerDocumentItem(
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            measurement_document=docs,
                            data_processing_time=data.title.data_processing_time,
                        ),
                        analyst=data.title.analyst,
                    )
                )

        return solution_analyzer_document

    def _get_measurement_document(self, sample: Sample) -> list[MeasurementDocument]:
        measurement_document = []

        for measurement_time, measurements in sample.measurements.items():
            if doc := self._create_sample_measurement(sample, measurement_time, {k: v for k, v in measurements.items() if k == OPTICAL_DENSITY}):
                measurement_document.append(doc)
            if doc := self._create_sample_measurement(sample, measurement_time, {k: v for k, v in measurements.items() if k != OPTICAL_DENSITY}):
                measurement_document.append(doc)

        return measurement_document

    def _create_sample_measurement(
        self, sample: Sample, measurement_time: str, measurements: dict[str, Measurement]
    ) -> MeasurementDocument:
        if not measurements:
            return None

        measurement_document = MeasurementDocument(
            measurement_identifier=random_uuid_str(),
            measurement_time=self._get_date_time(measurement_time),
            sample_document=SampleDocument(
                sample_identifier=sample.name,
                batch_identifier=sample.batch,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(device_type=SOLUTION_ANALYZER)
                ]
            ),
        )

        if OPTICAL_DENSITY in measurements:
            measurement_document.absorbance = TQuantityValueMilliAbsorbanceUnit(value=measurements[OPTICAL_DENSITY].concentration_value)
            if measurement_document.absorbance.value in (None, NaN):
                return None
        else:
            measurement_document.analyte_aggregate_document = AnalyteAggregateDocument(
                analyte_document=[
                    AnalyteDocument(
                        analyte_name=name,
                        molar_concentration=TQuantityValueMillimolePerLiter(
                            value=measurements[name].concentration_value
                        ),
                    )
                    for name in sorted(measurements)
                    if measurements[name].concentration_value not in (None, NaN)
                ]
            )
            if not measurement_document.analyte_aggregate_document.analyte_document:
                return None
        return measurement_document

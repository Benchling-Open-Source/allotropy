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
from allotropy.allotrope.models.shared.definitions.definitions import InvalidJsonFloat
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
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import Data, Sample
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
            solution_analyzer_document.append(
                SolutionAnalyzerDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_document=self._get_measurement_document(sample),
                        data_processing_time=sample.measurement_time,
                    ),
                    analyst=data.title.analyst,
                )
            )
        # TODO: Remove this once the solution analyzer schema is updated to handle NaN values
        for solution_analyzer_document_item in list(solution_analyzer_document):
            self.__drop_nan_from_measurement_documents(
                solution_analyzer_document_item.measurement_aggregate_document.measurement_document)
            # if the document does not have any measurement document, remove the document item
            if not solution_analyzer_document_item.measurement_aggregate_document.measurement_document:
                solution_analyzer_document.remove(solution_analyzer_document_item)

        return solution_analyzer_document

    def _get_measurement_document(self, sample: Sample) -> list[MeasurementDocument]:
        analytes = sample.analyte_list.analytes
        measurement_document = []
        if any(analyte.name == OPTICAL_DENSITY for analyte in analytes):
            measurement_document.append(
                self._create_sample_measurement(sample, include_analyte=False)
            )
        if len(analytes) > 1:
            measurement_document.append(
                self._create_sample_measurement(sample, include_analyte=True)
            )
        return measurement_document

    def _create_sample_measurement(
            self, sample: Sample, *, include_analyte: bool
    ) -> MeasurementDocument:
        non_aggregrable_dict = sample.analyte_list.non_aggregrable_dict
        absorbance = None
        if non_aggregrable_dict and OPTICAL_DENSITY in non_aggregrable_dict:
            optical_density = non_aggregrable_dict["optical_density"][0]
            absorbance = TQuantityValueMilliAbsorbanceUnit(value=optical_density.value)
        measurement_document = MeasurementDocument(
            measurement_identifier=random_uuid_str(),
            measurement_time=self._get_date_time(sample.measurement_time),
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
        if absorbance and not include_analyte:
            measurement_document.absorbance = absorbance
        if include_analyte and len(sample.analyte_list.analytes) > 1:
            measurement_document.analyte_aggregate_document = AnalyteAggregateDocument(
                analyte_document=self._get_analyte_document(sample)
            )
        return measurement_document

    def _get_analyte_document(self, sample: Sample) -> list[AnalyteDocument]:
        analyte_document = []
        for analyte in sample.analyte_list.analytes:
            if analyte.name == OPTICAL_DENSITY:
                continue
            analyte_document.append(
                AnalyteDocument(
                    analyte_name=analyte.name,
                    molar_concentration=TQuantityValueMillimolePerLiter(
                        value=analyte.concentration_value
                    ),
                )
            )
        return analyte_document

    def __drop_nan_from_measurement_documents(self, measurement_documents: list[MeasurementDocument]):
        for measurement_document in list(measurement_documents):
            if measurement_document.absorbance and isinstance(measurement_document.absorbance.value, InvalidJsonFloat):
                measurement_document.absorbance = None
            if measurement_document.analyte_aggregate_document:
                for analyte_document in list(measurement_document.analyte_aggregate_document.analyte_document):
                    if isinstance(analyte_document.molar_concentration.value, InvalidJsonFloat):
                        measurement_document.analyte_aggregate_document.analyte_document.remove(analyte_document)
                if not measurement_document.analyte_aggregate_document.analyte_document:
                    measurement_document.analyte_aggregate_document = None
            # if document does not comply with uv-absorbance detection or metabolite detection, remove the document
            if (not measurement_document.absorbance and
                    not measurement_document.analyte_aggregate_document):
                measurement_documents.remove(measurement_document)

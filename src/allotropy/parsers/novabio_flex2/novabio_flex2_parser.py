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
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import (
    Analyte,
    Data,
    Sample,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

# TODO: Validate these
MODEL_NUMBER = "Flex2"
SOFTWARE_NAME = "NovaBio Flex"
DEVICE_TYPE = "solution-analyzer"
PRODUCT_MANUFACTURER = "Nova Biomedical"


class NovaBioFlexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "NovaBio Flex2"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        return self._get_model(
            Data.create(named_file_contents), named_file_contents.original_file_name
        )

    def _get_model(self, data: Data, file_name: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest",
            solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
                solution_analyzer_document=self._get_solution_analyzer_document(data),
                device_system_document=DeviceSystemDocument(
                    model_number=MODEL_NUMBER,
                    product_manufacturer=PRODUCT_MANUFACTURER,
                    device_identifier=data.title.device_identifier,
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    software_name=SOFTWARE_NAME,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
            ),
        )

    def _get_solution_analyzer_document(
        self, data: Data
    ) -> list[SolutionAnalyzerDocumentItem]:
        return [
            SolutionAnalyzerDocumentItem(
                analyst=data.sample_list.analyst,
                measurement_aggregate_document=MeasurementAggregateDocument(
                    data_processing_time=self._get_date_time(
                        data.title.processing_time
                    ),
                    measurement_document=self._get_measurements_from_sample(sample),
                ),
            )
            for sample in data.sample_list.samples
        ]

    def _get_measurements_from_sample(
        self, sample: Sample
    ) -> list[MeasurementDocument]:
        # get analytes and properties included in the output file
        measurements = []
        if sample.analytes:
            measurements.append(self._get_analytes_measurement(sample))

        if sample.properties:
            measurement = MeasurementDocument(
                measurement_identifier=random_uuid_str(),
                measurement_time=self._get_date_time(sample.measurement_time),
                sample_document=SampleDocument(
                    sample_identifier=sample.identifier,
                    description=sample.sample_type,
                    batch_identifier=sample.batch_identifier,
                ),
                device_control_aggregate_document=DeviceControlAggregateDocument(
                    device_control_document=[
                        DeviceControlDocumentItem(device_type=DEVICE_TYPE)
                    ]
                ),
            )
            # TODO: break into other measurement types and report all properties
            for name, property_ in sample.properties.items():
                setattr(measurement, name, property_)

            measurements.append(measurement)

        return measurements

    def _get_analytes_measurement(self, sample: Sample) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_identifier=random_uuid_str(),
            measurement_time=self._get_date_time(sample.measurement_time),
            sample_document=SampleDocument(
                sample_identifier=sample.identifier,
                description=sample.sample_type,
                batch_identifier=sample.batch_identifier,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=DEVICE_TYPE,
                        detection_type="metabolite-detection",
                    )
                ]
            ),
            analyte_aggregate_document=AnalyteAggregateDocument(
                analyte_document=[
                    self._get_analyte_document(analyte) for analyte in sample.analytes
                ]
            ),
        )

    def _get_analyte_document(self, analyte: Analyte) -> AnalyteDocument:
        analyte_document = AnalyteDocument(analyte_name=analyte.name)

        mappings = {
            "mmol/L": "molar_concentration",
            "g/L": "mass_concentration",
            "mL/L": "volume_concentration",
        }

        try:
            concentration_name = mappings[analyte.concentration.unit]
        except KeyError as e:
            msg = f"Unknow concentration unit {analyte.concentration.unit}"
            raise AllotropeConversionError(msg) from e

        setattr(analyte_document, concentration_name, analyte.concentration)

        return analyte_document

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
            if doc := self._create_sample_measurement(
                sample,
                measurement_time,
                {k: v for k, v in measurements.items() if k == OPTICAL_DENSITY},
            ):
                measurement_document.append(doc)
            if doc := self._create_sample_measurement(
                sample,
                measurement_time,
                {k: v for k, v in measurements.items() if k != OPTICAL_DENSITY},
            ):
                measurement_document.append(doc)

        return measurement_document

    def _create_analyte_document(
        self, measurement: Measurement
    ) -> tuple[AnalyteDocument, str | None]:
        value = (
            measurement.concentration_value
            if isinstance(measurement.concentration_value, float)
            else -1
        )
        analyte = AnalyteDocument(
            analyte_name=measurement.name,
            molar_concentration=TQuantityValueMillimolePerLiter(value=value),
        )
        error = measurement.error

        if measurement.unit == "g/L":
            analyte = AnalyteDocument(
                analyte_name=measurement.name,
                mass_concentration=TQuantityValueGramPerLiter(value=value),
            )
        elif measurement.unit == "mL/L":
            analyte = AnalyteDocument(
                analyte_name=measurement.name,
                volume_concentration=TQuantityValueMilliliterPerLiter(value=value),
            )
        elif measurement.unit == "mmol/L":
            analyte = AnalyteDocument(
                analyte_name=measurement.name,
                molar_concentration=TQuantityValueMillimolePerLiter(value=value),
            )
        elif measurement.unit == "U/L":
            if measurement.name == "ldh":
                analyte = AnalyteDocument(
                    analyte_name=measurement.name,
                    molar_concentration=TQuantityValueMillimolePerLiter(
                        value=value * 0.0167 if value > 0 else value
                    ),
                )
            else:
                error = f"Invalid unit for {measurement.name}: {measurement.unit}"
        else:
            error = f"Invalid unit for analyte: {measurement.unit}, value values are: g/L, mL/L, mmol/L"

        return analyte, error

    def _create_sample_measurement(
        self,
        sample: Sample,
        measurement_time: str,
        measurements: dict[str, Measurement],
    ) -> MeasurementDocument | None:
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

        errors: list[ErrorDocumentItem] = []
        if OPTICAL_DENSITY in measurements:
            measurement = measurements[OPTICAL_DENSITY]
            value = (
                measurement.concentration_value
                if measurement.concentration_value is not NaN
                else -1
            )
            measurement_document.absorbance = TQuantityValueMilliAbsorbanceUnit(
                value=value
            )

            # TODO: always add value, add error to error document
            if measurement.concentration_value is NaN:
                return None
        else:
            analytes = []
            for name in sorted(measurements):
                analyte, error = self._create_analyte_document(measurements[name])
                # TODO: always write analyte, add error to error document
                if not error:
                    analytes.append(analyte)

            if analytes:
                measurement_document.analyte_aggregate_document = (
                    AnalyteAggregateDocument(analyte_document=analytes)
                )
            else:
                return None

        if errors:
            measurement_document.error_aggregate_document = ErrorAggregateDocument(
                error_document=errors
            )

        return measurement_document

from allotropy.allotrope.models.adm.cell_culture_analyzer.benchling._2023._09.cell_culture_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    SampleDocument,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import Data, Sample
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class NovaBioFlexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "NovaBio Flex2"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        return self._get_model(Data.create(named_file_contents))

    def _get_model(self, data: Data) -> Model:
        return Model(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_identifier=random_uuid_str(),
                data_processing_time=self._get_date_time(data.title.processing_time),
                analyst=data.sample_list.analyst,
                device_system_document=DeviceSystemDocument(
                    model_number="NovaBio Flex2",
                    device_identifier=data.title.device_identifier,
                ),
                measurement_document=self._get_measurement_document(data),
            ),
        )

    def _get_measurement_document(self, data: Data) -> list[MeasurementDocumentItem]:
        # get analytes and properties included in the output file
        return [
            self._get_measurement_from_sample(sample)
            for sample in data.sample_list.samples
        ]

    def _get_measurement_from_sample(self, sample: Sample) -> MeasurementDocumentItem:
        sample_measurement = MeasurementDocumentItem(
            sample_document=SampleDocument(
                sample_identifier=sample.identifier,
                sample_role_type=sample.role_type,
                batch_identifier=sample.batch_identifier,
            ),
            measurement_time=self._get_date_time(sample.measurement_time),
            analyte_aggregate_document=AnalyteAggregateDocument(
                analyte_document=[
                    AnalyteDocumentItem(
                        analyte_name=analyte.name,
                        molar_concentration=analyte.molar_concentration,
                    )
                    for analyte in sample.analytes
                ]
            ),
        )

        # properties are not included under the analyte aggregate document
        # and are added directly to the measurement document instead
        for name, property_ in sample.properties.items():
            setattr(sample_measurement, name, property_)

        return sample_measurement

from allotropy.allotrope.models.cell_culture_analyzer_benchling_2023_09_cell_culture_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    SampleDocument,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_reader import (
    RocheCedexBiohtReader,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import Data, Sample
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class RocheCedexBiohtParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        reader = RocheCedexBiohtReader(contents)
        return self._get_model(Data.create(reader))

    def _get_model(self, data: Data) -> Model:
        return Model(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_identifier=random_uuid_str(),
                data_processing_time=self._get_date_time(
                    data.title.data_processing_time
                ),
                analyst=data.title.analyst,
                device_system_document=DeviceSystemDocument(
                    model_number=data.title.model_number,
                    device_serial_number=data.title.device_serial_number,
                ),
                measurement_document=self._get_measurement_document(data),
            )
        )

    def _get_measurement_document(self, data: Data) -> list[MeasurementDocumentItem]:
        measurement_document = []
        for sample in data.samples:
            measurement_document.extend(self._get_measurements_from_sample(sample))
        return measurement_document

    def _get_measurements_from_sample(
        self, sample: Sample
    ) -> list[MeasurementDocumentItem]:
        sample_measurements = [
            self._create_sample_measurement(sample)
            for _ in range(sample.analyte_list.num_measurement_docs)
        ]

        for (
            analyte_name,
            molar_concentrations,
        ) in sample.analyte_list.molar_concentration_dict.items():
            for sample_measurement, molar_concentration in zip(
                sample_measurements, molar_concentrations
            ):
                sample_measurement.analyte_aggregate_document.analyte_document.append(  # type: ignore[union-attr]
                    AnalyteDocumentItem(
                        analyte_name=analyte_name,
                        molar_concentration=molar_concentration,
                    )
                )

        for analyte_name, values in sample.analyte_list.non_aggregrable_dict.items():
            for sample_measurement, value in zip(sample_measurements, values):
                setattr(sample_measurement, analyte_name, value)

        return sample_measurements

    def _create_sample_measurement(self, sample: Sample) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            sample_document=SampleDocument(
                sample_identifier=sample.name,
                sample_role_type=sample.role_type,
                batch_identifier=sample.batch,
            ),
            measurement_time=self._get_date_time(sample.measurement_time),
            analyte_aggregate_document=AnalyteAggregateDocument(analyte_document=[]),
        )

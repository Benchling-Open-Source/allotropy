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
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_bioht.constants import (
    MOLAR_CONCENTRATION_CLS_BY_UNIT,
    NON_ANALYTE_PROPERTIES,
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
        docs: list[MeasurementDocumentItem] = []

        for measurement_time, measurements in sample.measurements.items():
            doc = MeasurementDocumentItem(
                sample_document=SampleDocument(
                    sample_identifier=sample.name,
                    batch_identifier=sample.batch,
                ),
                measurement_time=self._get_date_time(measurement_time),
                analyte_aggregate_document=AnalyteAggregateDocument(
                    analyte_document=[]
                ),
            )
            analyte_documents = []
            for name in sorted(measurements):
                measurement = measurements[name]
                if analyte_cls := NON_ANALYTE_PROPERTIES.get(name):
                    setattr(
                        doc, name, analyte_cls(value=measurement.concentration_value)
                    )
                else:
                    molar_concentration_item_cls = MOLAR_CONCENTRATION_CLS_BY_UNIT.get(
                        measurement.unit or ""
                    )
                    if not molar_concentration_item_cls:
                        continue
                    analyte_documents.append(
                        AnalyteDocumentItem(
                            analyte_name=name,
                            molar_concentration=molar_concentration_item_cls(
                                value=measurement.concentration_value
                            ),
                        )
                    )
            doc.analyte_aggregate_document.analyte_document = analyte_documents
            docs.append(doc)

        return docs

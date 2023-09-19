import uuid

from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    ContainerType,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
)
from allotropy.allotrope.models.shared.definitions.custom import TQuantityValueNumber
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.agilent_gen5.fluorescence_data_point import FluorescenceDataPoint
from allotropy.parsers.agilent_gen5.plate_data import PlateData


class FluorescencePlateData(PlateData):
    read_mode = ReadMode.FLUORESCENCE
    data_point_cls = FluorescenceDataPoint

    def to_allotrope(self, measurement_docs: list[MeasurementDocumentItem]) -> Model:
        return Model(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_identifier=str(uuid.uuid4()),
                measurement_time=self.datetime,
                analytical_method_identifier=self.protocol_file_path,
                experimental_data_identifier=self.experiment_file_path,
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(len(self.wells)),
                # TODO read_type=self.read_type.value?,
                measurement_document=measurement_docs,
            )
        )

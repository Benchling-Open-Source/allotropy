import uuid

from allotropy.allotrope.models.luminescence_benchling_2023_09_luminescence import (
    ContainerType,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
)
from allotropy.allotrope.models.shared.definitions.custom import TQuantityValueNumber
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.agilent_gen5.luminescence_data_point import LuminescenceDataPoint
from allotropy.parsers.agilent_gen5.plate_data import PlateData


class LuminescencePlateData(PlateData):
    read_mode = ReadMode.LUMINESCENCE
    data_point_cls = LuminescenceDataPoint

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

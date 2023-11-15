# mypy: disallow_any_generics = False

from abc import ABC, abstractmethod
from typing import Any, Optional

from allotropy.allotrope.models.shared.components.plate_reader import (
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.parsers.agilent_gen5.constants import (
    ReadMode,
    ReadType,
    READTYPE_TO_DIMENSIONS,
)


class DataPoint(ABC):
    read_mode: ReadMode
    unit: str

    def __init__(
        self,
        read_type: ReadType,
        measurements: list[Any],
        well_location: str,
        plate_barcode: str,
        sample_identifier: Optional[str],
        concentration: Optional[float],
        processed_data: list[list],
        temperature: Optional[float],
    ):
        self.read_type = read_type
        self.measurements = measurements
        self.well_location = well_location
        self.plate_barcode = plate_barcode
        self.sample_identifier = sample_identifier
        self.concentration = concentration
        self.processed_data = processed_data
        self.temperature = temperature

    def generate_sample_doc(self) -> SampleDocument:
        sample_doc = SampleDocument(
            well_location_identifier=self.well_location,
            plate_barcode=self.plate_barcode,
            # TODO extract from Layout and map values to Allotrope's enum
            # sample_role_type=self.sample_role_type,
        )
        if self.sample_identifier:
            sample_doc.sample_identifier = self.sample_identifier
        return sample_doc

    def generate_data_cube(self) -> TDatacube:
        structure_dimensions = READTYPE_TO_DIMENSIONS[self.read_type]
        structure_measures = [("double", self.read_mode.lower(), self.unit)]
        num_measurements_with_temperature = 3
        if self.read_type == ReadType.AREASCAN:
            data_dimensions = [
                [m[0] for m in self.measurements],
                [m[1] for m in self.measurements],
            ]
            data_measures = [[m[2] for m in self.measurements]]
        elif (
            self.read_type == ReadType.KINETIC
            and len(self.measurements[0]) == num_measurements_with_temperature
        ):
            structure_measures.append(("double", "temperature", "C"))
            data_dimensions = [[m[0] for m in self.measurements]]
            data_measures = [
                [m[1] for m in self.measurements],
                [m[2] for m in self.measurements],
            ]
        else:
            data_dimensions = [[m[0] for m in self.measurements]]
            data_measures = [[m[1] for m in self.measurements]]

        return TDatacube(
            label=f"{self.read_type.value.lower()} data",
            cube_structure=TDatacubeStructure(
                [
                    TDatacubeComponent(FieldComponentDatatype(data_type), concept, unit)
                    for data_type, concept, unit in structure_dimensions
                ],
                [
                    TDatacubeComponent(FieldComponentDatatype(data_type), concept, unit)
                    for data_type, concept, unit in structure_measures
                ],
            ),
            data=TDatacubeData(data_dimensions, data_measures),  # type: ignore[arg-type]
        )

    def processed_data_doc(self) -> ProcessedDataAggregateDocument:
        return ProcessedDataAggregateDocument(
            [
                ProcessedDataDocumentItem(data[1], data_processing_description=data[0])
                for data in self.processed_data
            ]
        )

    @abstractmethod
    def to_measurement_doc(self) -> Any:
        raise NotImplementedError

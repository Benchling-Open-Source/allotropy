from typing import Any, Union

from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    ContainerType as FluorescenceContainerType,
    MeasurementAggregateDocument as FluorescenceMeasurementAggregateDocument,
    Model as FluorescenceModel,
)
from allotropy.allotrope.models.luminescence_benchling_2023_09_luminescence import (
    ContainerType as LuminescenceContainerType,
    MeasurementAggregateDocument as LuminescenceMeasurementAggregateDocument,
    Model as LuminescenceModel,
)
from allotropy.allotrope.models.shared.definitions.custom import TQuantityValueNumber
from allotropy.allotrope.models.ultraviolet_absorbance_benchling_2023_09_ultraviolet_absorbance import (
    ContainerType as AbsorbanceContainerType,
    MeasurementAggregateDocument as AbsorbanceMeasurementAggregateDocument,
    Model as AbsorbanceModel,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import Data
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.agilent_gen5.plate_data import PlateData
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5Parser(VendorParser):
    def _create_model(
        self, plate_data: PlateData
    ) -> Union[AbsorbanceModel, FluorescenceModel, LuminescenceModel]:
        measurement_docs = plate_data.results.measurement_docs
        if plate_data.read_data.read_mode == ReadMode.ABSORBANCE:
            return AbsorbanceModel(
                measurement_aggregate_document=AbsorbanceMeasurementAggregateDocument(
                    measurement_identifier=random_uuid_str(),
                    measurement_time=self._get_date_time(
                        plate_data.header_data.datetime
                    ),
                    analytical_method_identifier=plate_data.file_paths.protocol_file_path,
                    experimental_data_identifier=plate_data.file_paths.experiment_file_path,
                    container_type=AbsorbanceContainerType.well_plate,
                    plate_well_count=TQuantityValueNumber(
                        len(plate_data.results.wells)
                    ),
                    measurement_document=measurement_docs,
                )
            )
        elif plate_data.read_data.read_mode == ReadMode.FLUORESCENCE:
            return FluorescenceModel(
                measurement_aggregate_document=FluorescenceMeasurementAggregateDocument(
                    measurement_identifier=random_uuid_str(),
                    measurement_time=self._get_date_time(
                        plate_data.header_data.datetime
                    ),
                    analytical_method_identifier=plate_data.file_paths.protocol_file_path,
                    experimental_data_identifier=plate_data.file_paths.experiment_file_path,
                    container_type=FluorescenceContainerType.well_plate,
                    plate_well_count=TQuantityValueNumber(
                        len(plate_data.results.wells)
                    ),
                    measurement_document=measurement_docs,
                )
            )
        elif plate_data.read_data.read_mode == ReadMode.LUMINESCENCE:
            return LuminescenceModel(
                measurement_aggregate_document=LuminescenceMeasurementAggregateDocument(
                    measurement_identifier=random_uuid_str(),
                    measurement_time=self._get_date_time(
                        plate_data.header_data.datetime
                    ),
                    analytical_method_identifier=plate_data.file_paths.protocol_file_path,
                    experimental_data_identifier=plate_data.file_paths.experiment_file_path,
                    container_type=LuminescenceContainerType.well_plate,
                    plate_well_count=TQuantityValueNumber(
                        len(plate_data.results.wells)
                    ),
                    measurement_document=measurement_docs,
                )
            )

        msg = msg_for_error_on_unrecognized_value(
            "read mode", plate_data.read_data.read_mode, ReadMode._member_names_
        )
        raise AllotropeConversionError(msg)

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        lines = read_to_lines(named_file_contents)
        section_lines_reader = SectionLinesReader(lines)
        data = Data.create(section_lines_reader)

        return self._create_model(data.plate_data)

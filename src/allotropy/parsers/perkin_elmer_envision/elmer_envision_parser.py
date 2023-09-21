from io import IOBase
from typing import Any, Optional, TypeVar
import uuid

from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    ContainerType,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
)
from allotropy.allotrope.models.shared.components.plate_reader import (
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValueNumber,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.perkin_elmer_envision.elmer_envision_structure import Data, Plate
from allotropy.parsers.vendor_parser import VendorParser

T = TypeVar("T")


def safe_value(cls: type[T], value: Optional[Any]) -> Optional[T]:
    return None if value is None else cls(value=value)  # type: ignore[call-arg]


class ElmerEnvisionParser(VendorParser):
    def _parse(self, raw_contents: IOBase, _: str) -> Model:
        reader = LinesReader(raw_contents)
        return self._get_model(Data.create(reader))

    def _get_model(self, data: Data) -> Model:
        if not self._check_fluorescence(data):
            msg = "Elmer envision currently only accepts fluorescence data"
            raise NotImplementedError(msg)

        if data.number_of_wells is None:
            msg = "Unable to get number of the wells in the plate"
            raise Exception(msg)

        return Model(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_identifier=str(uuid.uuid4()),
                measurement_time=self._get_measurement_time(data),
                analytical_method_identifier=data.basic_assay_info.protocol_id,
                experimental_data_identifier=data.basic_assay_info.assay_id,
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(value=data.number_of_wells),
                device_system_document=DeviceSystemDocument(
                    model_number=data.instrument.serial_number,
                    device_identifier=data.instrument.nickname,
                ),
                measurement_document=self._get_measurement_document(data),
            )
        )

    def _check_fluorescence(self, data: Data) -> bool:
        absorbance_patterns = ["ABS", "Absorbance"]
        luminescence_patterns = ["LUM", "Luminescence"]

        for pattern in absorbance_patterns + luminescence_patterns:
            if pattern in data.labels.label:
                return False

        return True

    def _get_measurement_time(self, data: Data) -> TDateTimeValue:
        dates = [
            plate.plate_info.measurement_time
            for plate in data.plates
            if plate.plate_info.measurement_time
        ]

        if dates:
            return self.get_date_time(min(dates))

        msg = "Unable to find valid measurement date"
        raise Exception(msg)

    def _get_device_control_aggregate_document(
        self, data: Data, plate: Plate
    ) -> DeviceControlAggregateDocument:
        ex_filter = data.labels.excitation_filter
        em_filter = data.labels.get_emission_filter(plate.plate_info.emission_filter_id)
        return DeviceControlAggregateDocument(
            [
                DeviceControlDocumentItem(
                    device_type="fluorescence detector",
                    detector_distance_setting__plate_reader_=safe_value(
                        TQuantityValueMillimeter, plate.plate_info.measured_height
                    ),
                    number_of_averages=safe_value(
                        TQuantityValueNumber, data.labels.number_of_flashes
                    ),
                    detector_gain_setting=data.labels.detector_gain_setting,
                    scan_position_setting__plate_reader_=data.labels.scan_position_setting,
                    detector_wavelength_setting=safe_value(
                        TQuantityValueNanometer,
                        em_filter.wavelength if em_filter else None,
                    ),
                    detector_bandwidth_setting=safe_value(
                        TQuantityValueNanometer,
                        em_filter.bandwidth if em_filter else None,
                    ),
                    excitation_wavelength_setting=safe_value(
                        TQuantityValueNanometer,
                        ex_filter.wavelength if ex_filter else None,
                    ),
                    excitation_bandwidth_setting=safe_value(
                        TQuantityValueNanometer,
                        ex_filter.bandwidth if ex_filter else None,
                    ),
                )
            ]
        )

    def _get_measurement_document(self, data: Data) -> list[MeasurementDocumentItem]:
        items = []
        for plate in data.plates:
            if plate.results is None:
                continue

            try:
                p_map = data.plate_maps[plate.plate_info.number]
            except KeyError as e:
                msg = f"Unable to find plate map of {plate.plate_info.barcode}"
                raise Exception(msg) from e

            device_control_document = self._get_device_control_aggregate_document(
                data, plate
            )

            items += [
                MeasurementDocumentItem(
                    sample_document=SampleDocument(
                        plate_barcode=plate.plate_info.barcode,
                        well_location_identifier=f"{result.col}{result.row}",
                        sample_role_type=p_map.get_sample_role_type(
                            result.col, result.row
                        ),
                    ),
                    device_control_aggregate_document=device_control_document,
                    processed_data_aggregate_document=ProcessedDataAggregateDocument(
                        processed_data_document=[
                            ProcessedDataDocumentItem(
                                processed_data=result.value,
                                data_processing_description="processed data",
                            ),
                        ]
                    ),
                    compartment_temperature=safe_value(
                        TQuantityValueDegreeCelsius,
                        plate.plate_info.chamber_temperature_at_start,
                    ),
                )
                for result in plate.results
            ]
        return items

from typing import Any, ClassVar, Optional
import uuid

from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueNanometer,
    TQuantityValueNumber,
)
from allotropy.parsers.moldev_softmax_pro.plate_block import (
    PlateBlock,
    split_wavelengths,
    WellData,
)
from allotropy.parsers.utils.values import assert_not_none, natural_sort_key, try_int


class FluorescenceOrLuminescencePlateBlock(PlateBlock):
    EXCITATION_WAVELENGTHS_IDX: ClassVar[int]

    def parse_read_mode_header(self, header: list[Optional[str]]) -> None:
        [
            excitation_wavelengths_str,
            self.cutoff,
            cutoff_filters_str,
            self.sweep_wave,
            self.sweep_wavelength,
            self.reads_per_well,
            self.pmt_gain,
            self.start_integration_time,
            self.end_integration_time,
            self.first_row,
            num_rows,
        ] = header[
            self.EXCITATION_WAVELENGTHS_IDX : self.EXCITATION_WAVELENGTHS_IDX + 11
        ]
        self.excitation_wavelengths = split_wavelengths(excitation_wavelengths_str)
        self.cutoff_filters = split_wavelengths(cutoff_filters_str)
        self.num_rows = assert_not_none(try_int(num_rows), "num_rows")


class FluorescencePlateBlock(FluorescenceOrLuminescencePlateBlock):
    READ_MODE = "Fluorescence"
    CONCEPT = "fluorescence"
    UNIT = "RFU"
    DATA_TYPE_IDX = 7
    EXCITATION_WAVELENGTHS_IDX = 20

    # TODO: the reason we can't factor out DeviceControlDocumentItem and the enclosing classes is because the
    # Fluorescence ASM model has these extra fields. We may be able to fix this by templating the PlateBlock
    # class on these classes, or some clever shared/models refactoring.
    def generate_device_control_doc(self) -> DeviceControlDocumentItem:
        device_control_doc = DeviceControlDocumentItem(
            detector_gain_setting=self.pmt_gain
        )

        if self.is_single_wavelength:
            device_control_doc.detector_wavelength_setting = TQuantityValueNanometer(
                self.wavelengths[0]
            )
        if self.excitation_wavelengths and len(self.excitation_wavelengths) == 1:
            device_control_doc.excitation_wavelength_setting = TQuantityValueNanometer(
                self.excitation_wavelengths[0]
            )
        if self.cutoff_filters and len(self.cutoff_filters) == 1:
            device_control_doc.wavelength_filter_cutoff_setting = (
                TQuantityValueNanometer(self.cutoff_filters[0])
            )

        return device_control_doc

    def generate_measurement_doc(
        self, well: str, well_data: WellData
    ) -> MeasurementDocumentItem:
        measurement = MeasurementDocumentItem(
            DeviceControlAggregateDocument([self.generate_device_control_doc()]),
            self.generate_sample_document(well),
        )

        if well_data.temperature is not None:
            measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                float(well_data.temperature)
            )

        if not well_data.is_empty:
            measurement.data_cube = self.generate_data_cube(well_data)

        if well_data.processed_data:
            measurement.processed_data_aggregate_document = (
                self.generate_processed_data_aggreate_document(well_data)
            )

        return measurement

    def to_allotrope(self) -> Any:
        wells = sorted(self.well_data.keys(), key=natural_sort_key)

        allotrope_file = Model(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(self.num_wells),
                measurement_document=[
                    self.generate_measurement_doc(well, self.well_data[well])
                    for well in wells
                ],
            )
        )

        return allotrope_file

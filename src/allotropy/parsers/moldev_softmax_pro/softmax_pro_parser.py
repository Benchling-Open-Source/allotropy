from typing import Union
import uuid

from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentFluorescence,
    DeviceControlDocumentItem as DeviceControlDocumentItemFluorescence,
    MeasurementAggregateDocument as MeasurementAggregateDocumentFluorescence,
    MeasurementDocumentItem as MeasurementDocumentItemFluorescence,
    Model as ModelFluorescence,
)
from allotropy.allotrope.models.luminescence_benchling_2023_09_luminescence import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentLuminescence,
    DeviceControlDocumentItem as DeviceControlDocumentItemLuminescence,
    MeasurementAggregateDocument as MeasurementAggregateDocumentLuminescence,
    MeasurementDocumentItem as MeasurementDocumentItemLuminescence,
    Model as ModelLuminescence,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueNanometer,
    TQuantityValueNumber,
)
from allotropy.allotrope.models.ultraviolet_absorbance_benchling_2023_09_ultraviolet_absorbance import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentAbsorbance,
    DeviceControlDocumentItem as DeviceControlDocumentItemAbsorbance,
    MeasurementAggregateDocument as MeasurementAggregateDocumentAbsorbance,
    MeasurementDocumentItem as MeasurementDocumentItemAbsorbance,
    Model as ModelAbsorbance,
)
from allotropy.exceptions import (
    AllotropeConversionError,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import Data, PlateBlock
from allotropy.parsers.utils.values import natural_sort_key
from allotropy.parsers.vendor_parser import VendorParser


class SoftmaxproParser(VendorParser):
    def to_allotrope(
        self, named_file_contents: NamedFileContents
    ) -> Union[ModelAbsorbance, ModelLuminescence, ModelFluorescence]:
        lines = read_to_lines(named_file_contents.contents, encoding=None)
        reader = CsvReader(lines)
        data = Data.create(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(
        self, _: str, data: Data
    ) -> Union[ModelAbsorbance, ModelLuminescence, ModelFluorescence]:
        plate_block = data.get_plate_block()
        if plate_block.plate_block_type == "Absorbance":
            return self.absorbance_to_allotrope(plate_block)
        elif plate_block.plate_block_type == "Luminescence":
            return self.luminescence_to_allotrope(plate_block)
        elif plate_block.plate_block_type == "Fluorescence":
            return self.fluorescence_to_allotrope(plate_block)

        error = "Unable to find valid plate block type."
        raise AllotropeConversionError(error)

    def fluorescence_to_allotrope(self, plate_block: PlateBlock) -> ModelFluorescence:
        measurement_document = []

        for well in sorted(plate_block.well_data.keys(), key=natural_sort_key):
            well_data = plate_block.well_data[well]

            # TODO: the reason we can't factor out DeviceControlDocumentItemFluorescence and the enclosing classes is because the
            # Fluorescence ASM model has these extra fields. We may be able to fix this by templating the PlateBlock
            # class on these classes, or some clever shared/models refactoring.
            device_control_doc = DeviceControlDocumentItemFluorescence(
                detector_gain_setting=plate_block.header.pmt_gain
            )

            if plate_block.is_single_wavelength:
                device_control_doc.detector_wavelength_setting = (
                    TQuantityValueNanometer(plate_block.header.wavelengths[0])
                )
            if (
                plate_block.header.excitation_wavelengths
                and len(plate_block.header.excitation_wavelengths) == 1
            ):
                device_control_doc.excitation_wavelength_setting = (
                    TQuantityValueNanometer(
                        plate_block.header.excitation_wavelengths[0]
                    )
                )
            if (
                plate_block.header.cutoff_filters
                and len(plate_block.header.cutoff_filters) == 1
            ):
                device_control_doc.wavelength_filter_cutoff_setting = (
                    TQuantityValueNanometer(plate_block.header.cutoff_filters[0])
                )

            measurement = MeasurementDocumentItemFluorescence(
                DeviceControlAggregateDocumentFluorescence([device_control_doc]),
                plate_block.generate_sample_document(well),
            )

            if well_data.temperature is not None:
                measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                    well_data.temperature
                )

            if not well_data.is_empty:
                measurement.data_cube = plate_block.generate_data_cube(well_data)

            if well_data.processed_data:
                measurement.processed_data_aggregate_document = (
                    plate_block.generate_processed_data_aggreate_document(well_data)
                )
            measurement_document.append(measurement)

        return ModelFluorescence(
            measurement_aggregate_document=MeasurementAggregateDocumentFluorescence(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(plate_block.header.num_wells),
                measurement_document=measurement_document,
            )
        )

    def luminescence_to_allotrope(self, plate_block: PlateBlock) -> ModelLuminescence:
        measurement_document = []
        for well in sorted(plate_block.well_data.keys(), key=natural_sort_key):
            well_data = plate_block.well_data[well]

            device_control_doc = DeviceControlDocumentItemLuminescence(
                detector_gain_setting=plate_block.header.pmt_gain
            )

            if plate_block.is_single_wavelength:
                device_control_doc.detector_wavelength_setting = (
                    TQuantityValueNanometer(plate_block.header.wavelengths[0])
                )

            measurement = MeasurementDocumentItemLuminescence(
                DeviceControlAggregateDocumentLuminescence([device_control_doc]),
                plate_block.generate_sample_document(well),
            )

            if well_data.temperature is not None:
                measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                    well_data.temperature
                )

            if not well_data.is_empty:
                measurement.data_cube = plate_block.generate_data_cube(well_data)

            if well_data.processed_data:
                measurement.processed_data_aggregate_document = (
                    plate_block.generate_processed_data_aggreate_document(well_data)
                )
            measurement_document.append(measurement)

        return ModelLuminescence(
            measurement_aggregate_document=MeasurementAggregateDocumentLuminescence(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(plate_block.header.num_wells),
                measurement_document=measurement_document,
            )
        )

    def absorbance_to_allotrope(self, plate_block: PlateBlock) -> ModelAbsorbance:
        measurement_document = []
        for well in sorted(plate_block.well_data.keys(), key=natural_sort_key):
            well_data = plate_block.well_data[well]

            device_control_doc = DeviceControlDocumentItemAbsorbance(
                detector_gain_setting=plate_block.header.pmt_gain
            )

            if plate_block.is_single_wavelength:
                device_control_doc.detector_wavelength_setting = (
                    TQuantityValueNanometer(plate_block.header.wavelengths[0])
                )

            measurement = MeasurementDocumentItemAbsorbance(
                DeviceControlAggregateDocumentAbsorbance([device_control_doc]),
                plate_block.generate_sample_document(well),
            )

            if well_data.temperature is not None:
                measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                    well_data.temperature
                )

            if not well_data.is_empty:
                measurement.data_cube = plate_block.generate_data_cube(well_data)

            if well_data.processed_data:
                measurement.processed_data_aggregate_document = (
                    plate_block.generate_processed_data_aggreate_document(well_data)
                )
            measurement_document.append(measurement)

        return ModelAbsorbance(
            measurement_aggregate_document=MeasurementAggregateDocumentAbsorbance(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(plate_block.header.num_wells),
                measurement_document=measurement_document,
            )
        )

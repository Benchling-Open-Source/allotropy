from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValuePicogramPerMilliliter,
)
from allotropy.allotrope.models.ultraviolet_absorbance_benchling_2023_09_ultraviolet_absorbance import (
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    MeasurementDocumentItem,
)
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.agilent_gen5.data_point import DataPoint


class AbsorbanceDataPoint(DataPoint):
    read_mode = ReadMode.ABSORBANCE
    unit = "mAU"

    def to_measurement_doc(self) -> MeasurementDocumentItem:
        measurement_doc = MeasurementDocumentItem(
            DeviceControlAggregateDocument([DeviceControlDocumentItem()]),
            self.generate_sample_doc(),
        )
        measurement_doc.data_cube = self.generate_data_cube()

        if self.concentration:
            measurement_doc.mass_concentration = TQuantityValuePicogramPerMilliliter(
                self.concentration
            )
        if self.processed_data:
            measurement_doc.processed_data_aggregate_document = (
                self.processed_data_doc()
            )
        if self.temperature:
            measurement_doc.compartment_temperature = TQuantityValueDegreeCelsius(
                float(self.temperature)
            )
        return measurement_doc

from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.docs.example.parser_calcdocs.extractor import ExampleExtractor
from allotropy.calcdocs.docs.example.parser_calcdocs.views import MeanView, SumView
from allotropy.calcdocs.docs.example.parser_code.measurement import Measurement
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.uuids import random_uuid_str


class ExampleParser:
    def read_data(self) -> list[Measurement]:
        return [
            Measurement(random_uuid_str(), "a", "x", 1.0, 3.0, 5.0),
            Measurement(random_uuid_str(), "a", "x", 2.0, 3.0, 5.0),
            Measurement(random_uuid_str(), "a", "x", 3.0, 7.0, 5.0),
            Measurement(random_uuid_str(), "a", "x", 4.0, 7.0, 5.0),
            Measurement(random_uuid_str(), "a", "y", 5.0, 11.0, 13.0),
            Measurement(random_uuid_str(), "a", "y", 6.0, 11.0, 13.0),
            Measurement(random_uuid_str(), "a", "y", 7.0, 15.0, 13.0),
            Measurement(random_uuid_str(), "a", "y", 8.0, 15.0, 13.0),
            Measurement(random_uuid_str(), "b", "x", 9.0, 19.0, 21.0),
            Measurement(random_uuid_str(), "b", "x", 10.0, 19.0, 21.0),
            Measurement(random_uuid_str(), "b", "x", 11.0, 23.0, 21.0),
            Measurement(random_uuid_str(), "b", "x", 12.0, 23.0, 21.0),
            Measurement(random_uuid_str(), "b", "y", 13.0, 27.0, 29.0),
            Measurement(random_uuid_str(), "b", "y", 14.0, 27.0, 29.0),
            Measurement(random_uuid_str(), "b", "y", 15.0, 31.0, 29.0),
            Measurement(random_uuid_str(), "b", "y", 16.0, 31.0, 29.0),
        ]

    def create_calculated_data(
        self, measurements: list[Measurement]
    ) -> list[CalculatedDocument]:
        elements = ExampleExtractor.get_elements(measurements)

        mean_view_data = MeanView().apply(elements)
        sum_view_data = MeanView(sub_view=SumView()).apply(elements)

        measurement_conf = MeasurementConfig(
            name="measurement",
            value="m",
        )

        sum_conf = CalculatedDataConfig(
            name="sumation",
            value="sum",
            view_data=sum_view_data,
            source_configs=(measurement_conf,),
        )

        mean_conf = CalculatedDataConfig(
            name="sum mean",
            value="mean",
            view_data=mean_view_data,
            source_configs=(sum_conf,),
        )

        configs = CalcDocsConfig(
            [
                sum_conf,
                mean_conf,
            ]
        )

        return [
            calc_doc
            for parent_calc_doc in configs.construct()
            for calc_doc in parent_calc_doc.iter_struct()
        ]

    def create_data(self) -> None:
        measurements = self.read_data()
        self.create_calculated_data(measurements)

from allotropy.calcdocs import (
    build_calc_docs,
    CalcDoc,
    FieldView,
    Measurement as CalcMeasurement,
    Node,
)
from allotropy.calcdocs.docs.example.parser_calcdocs.extractor import ExampleExtractor
from allotropy.calcdocs.docs.example.parser_code.measurement import Measurement
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def _example_nodes() -> list[Node]:
    m = CalcMeasurement("measurement", field="m")
    summation = CalcDoc("sumation", field="sum", sources=[m], view="mean_sum")
    mean = CalcDoc("sum mean", field="mean", sources=[summation], view="mean")
    return [m, summation, mean]


EXAMPLE_NODES: list[Node] = _example_nodes()


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
        views = {
            "mean": FieldView("mean").apply(elements),
            "mean_sum": FieldView("mean", sub_view=FieldView("sum")).apply(elements),
        }
        return build_calc_docs(nodes=EXAMPLE_NODES, views=views)

    def create_data(self) -> None:
        measurements = self.read_data()
        self.create_calculated_data(measurements)

from allotropy.calcdocs.docs.example.parser_code.measurement import Measurement
from allotropy.calcdocs.extractor import Element, Extractor


class ExampleExtractor(Extractor[Measurement]):
    @classmethod
    def to_element(cls, measurement: Measurement) -> Element:
        return Element(
            uuid=measurement.uuid,
            data={
                "sid": measurement.sid,
                "tid": measurement.tid,
                "m": measurement.m,
                "sum": measurement.sum_,
                "mean": measurement.mean,
            },
        )

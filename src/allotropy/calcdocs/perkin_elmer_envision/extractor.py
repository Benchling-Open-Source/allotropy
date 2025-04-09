from allotropy.calcdocs.extractor import Element, Extractor
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    Result,
)


class PerkinElmerEnvisionExtractor(Extractor[Result]):
    @classmethod
    def to_element(cls, result: Result) -> Element:
        return Element(
            uuid=result.uuid,
            data={
                "col": result.col,
                "row": result.row,
                "value": result.value,
            },
        )

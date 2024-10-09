from collections.abc import Callable
from typing import Generic, TypeVar

from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue

Data = TypeVar("Data")
Model = TypeVar("Model")


class SchemaMapper(Generic[Data, Model]):
    # The manifest of the schema this mapper supports
    MANIFEST: str

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data) -> Model:
        raise NotImplementedError

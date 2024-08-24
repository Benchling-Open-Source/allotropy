from typing import Generic, TypeVar

Data = TypeVar("Data")
Model = TypeVar("Model")


class SchemaMapper(Generic[Data, Model]):
    def __init__(self, asm_converter_name: str) -> None:
        self.converter_name = asm_converter_name

    def map_model(self, data: Data) -> Model:
        raise NotImplementedError

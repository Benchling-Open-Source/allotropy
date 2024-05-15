from abc import ABC, abstractmethod
from typing import Any, ClassVar

from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)


class Parser(ABC):
    MANIFEST: ClassVar[str]

    def __init__(self, asm_dict: dict[str, Any]):
        self.asm_dict = asm_dict
        self.measurement_docs = self.get_measurement_docs()
        self.calc_docs = self.get_calc_docs()

    @abstractmethod
    def get_measurement_docs(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_calc_docs(self) -> dict[str, Any]:
        pass

    def build_data_source(self, data_source: dict[str, Any]) -> DataSource:
        data_source_id = data_source["data source identifier"]
        if measurement_doc := self.measurement_docs.get(data_source_id):
            return DataSource(
                feature=data_source["data source feature"],
                reference=Referenceable(uuid=measurement_doc["measurement identifier"]),
            )
        elif calc_doc := self.calc_docs.get(data_source_id):
            return DataSource(
                feature=calc_doc["calculated data name"],
                reference=self.build_calc_doc(calc_doc),
            )

        msg = f"Unable to find data source '{data_source_id}'"
        raise ValueError(msg)

    def build_calc_doc(self, calc_doc: dict[str, Any]) -> CalculatedDocument:
        return CalculatedDocument(
            uuid=calc_doc["calculated data identifier"],
            name=calc_doc["calculated data name"],
            value=calc_doc["calculated datum"]["value"],
            data_sources=[
                self.build_data_source(data_source)
                for data_source in calc_doc["data source aggregate document"][
                    "data source document"
                ]
            ],
        )

    def parse(self) -> dict[str, CalculatedDocument]:
        calc_docs = [
            self.build_calc_doc(calc_doc) for calc_doc in self.calc_docs.values()
        ]
        return {calc_doc.uuid: calc_doc for calc_doc in calc_docs}

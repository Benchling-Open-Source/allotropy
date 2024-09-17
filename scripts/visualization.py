#!/usr/bin/env python

import argparse
import json
from typing import Any

from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.calculated_data_documents.visualization import (
    visualize_graph,
)


class Parser:
    def __init__(self, asm_dict: dict[str, Any]):
        self.asm_dict = asm_dict
        self.measurement_docs = self.get_measurement_docs()
        self.calc_docs = self.get_calc_docs()

    def get_measurement_docs(self) -> dict[str, Any]:
        measurement_agg_doc = "measurement aggregate document"
        measurement_document = "measurement document"
        return {
            measurement_doc["measurement identifier"]: measurement_doc
            for qpcr_doc in self.asm_dict["qPCR aggregate document"]["qPCR document"]
            for measurement_doc in qpcr_doc[measurement_agg_doc][measurement_document]
        }

    def get_calc_docs(self) -> dict[str, Any]:
        qpcr_doc = self.asm_dict["qPCR aggregate document"]
        calculated_agg_document = qpcr_doc["calculated data aggregate document"]
        return {
            calc_doc["calculated data identifier"]: calc_doc
            for calc_doc in calculated_agg_document["calculated data document"]
        }

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
        data_source_agg = calc_doc["data source aggregate document"]
        data_sources = data_source_agg["data source document"]
        return CalculatedDocument(
            uuid=calc_doc["calculated data identifier"],
            name=calc_doc["calculated data name"],
            value=calc_doc["calculated datum"]["value"],
            data_sources=[self.build_data_source(source) for source in data_sources],
        )

    def parse(self) -> dict[str, CalculatedDocument]:
        calc_docs = [
            self.build_calc_doc(calc_doc) for calc_doc in self.calc_docs.values()
        ]
        return {calc_doc.uuid: calc_doc for calc_doc in calc_docs}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="visualization",
        description="Graph visualization for calculated data document structure",
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="asm json file to visualize",
    )
    parser.add_argument(
        "calculated_document_name",
        type=str,
        help="name of calculated data document to visualize",
    )
    return parser.parse_args()


def read_json_file(path: str) -> dict[str, Any]:
    with open(path) as f:
        data: dict[str, Any] = json.load(f)
    return data


def main() -> None:
    args = parse_args()
    data = read_json_file(args.input_file)
    calc_docs = Parser(data).parse()
    visualize_graph(calc_docs, args.calculated_document_name)


if __name__ == "__main__":
    main()

#!/usr/bin/env python

import argparse
import json
from typing import Any

from parsers.parser import Parser
from parsers.pcr import QpcrParser

from allotropy.parsers.utils.calculated_data_documents.visualization import (
    visualize_graph,
)

PARSERS: list[type[Parser]] = [
    QpcrParser,
]

MANIFEST_TO_PARSER: dict[str, type[Parser]] = {
    parser.MANIFEST: parser for parser in PARSERS
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="visualization",
        description="Calculated data document graph visualization",
    )
    parser.add_argument("input_file", type=str, help="json file to visualize")
    parser.add_argument(
        "calculated_document_type",
        type=str,
        help="type of calculated data document to graph",
    )
    return parser.parse_args()


def read_json_file(path: str) -> dict[str, Any]:
    try:
        with open(path) as f:
            data: dict[str, Any] = json.load(f)
        return data
    except FileNotFoundError as e:
        msg = f"Unable to find json file '{path}'"
        raise FileNotFoundError(msg) from e
    except json.decoder.JSONDecodeError as e:
        msg = f"Unable to decode '{path} as json'"
        raise ValueError(msg) from e


def get_manifest(asm_dict: dict[str, Any]) -> str:
    if "$asm.manifest" not in asm_dict:
        msg = "File provided does not contain a supported ASM manifest"
        raise ValueError(msg)
    return str(asm_dict["$asm.manifest"])


def get_parser(manifest: str) -> type[Parser]:
    if parser := MANIFEST_TO_PARSER.get(manifest):
        return parser
    msg = f"Unable to find parser for manifest '{manifest}'"
    raise ValueError(msg)


def main() -> None:
    args = parse_args()
    data = read_json_file(args.input_file)
    manifest = get_manifest(data)
    parser = get_parser(manifest)
    calc_docs = parser(data).parse()
    visualize_graph(calc_docs, args.calculated_document_type)


if __name__ == "__main__":
    main()

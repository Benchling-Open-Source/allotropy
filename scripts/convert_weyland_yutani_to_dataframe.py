#!/usr/bin/env python

"""Convert Weyland-Yutani data to dataframe."""

import argparse
import sys
from typing import Any

import pandas as pd

from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_model_from_io
from allotropy.types import IOType


def main() -> None:
    """Main driver."""
    args = parse_args()
    for filename in args.filenames:
        with open(filename) as reader:
            handle(filename, reader)


def extract_well_data(model: Any) -> list[Any]:
    """Get (col, row, reading) from data."""

    def _split(loc: Any) -> tuple:  # type: ignore[type-arg]
        return (loc[0], int(loc[1:]))

    return [
        (*_split(doc.sample_document.well_location_identifier), 0.0)
        for doc in model.measurement_aggregate_document.measurement_document
    ]


def handle(filename: str, reader: IOType) -> None:
    """Extract and show data from a single model."""
    try:
        model = allotrope_model_from_io(reader, filename, Vendor.EXAMPLE_WEYLAND_YUTANI)
        well_data = extract_well_data(model)
        df = pd.DataFrame(well_data, columns=["col", "row", "reading"])
        print(df)
    except Exception as exc:
        print(f"Unable to read {filename}: {exc}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", type=str, nargs="+", help="input file(s)")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()

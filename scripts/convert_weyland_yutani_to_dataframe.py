#!/usr/bin/env python

"""Convert Weyland-Yutani data to dataframe."""

import argparse
import sys

import pandas as pd

from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_model_from_io


def main():
    """Main driver."""
    args = parse_args()
    if args.filenames:
        for filename in args.filenames:
            with open(filename) as reader:
                handle(filename, reader)
    else:
        handle("<stdin>", sys.stdin)


def extract_well_data(model):
    """Get (col, row, reading) from data."""

    def _split(loc):
        return (loc[0], int(loc[1:]))

    return [
        (*_split(doc.sample_document.well_location_identifier), 0.0)
        for doc in model.measurement_aggregate_document.measurement_document
    ]


def handle(filename, reader):
    """Extract and show data from a single model."""
    try:
        model = allotrope_model_from_io(reader, filename, Vendor.EXAMPLE_WEYLAND_YUTANI)
        well_data = extract_well_data(model)
        df = pd.DataFrame(well_data, columns=["col", "row", "reading"])
        print(df)  # noqa: T201
        pass
    except Exception as exc:
        print(f"Unable to read {filename}: {exc}", file=sys.stderr)  # noqa: T201


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", type=str, nargs="+", help="input file(s)")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""Show CSV file as JSON."""

import argparse
import json

from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_io


def main() -> None:
    """Main driver."""
    args = parse_args()
    vendor = Vendor[args.vendor]
    with open(args.infile) as reader:
        asm_schema = allotrope_from_io(reader, args.infile, vendor)
    if args.outfile:
        with open(args.outfile, "w") as out:
            json.dump(asm_schema, out, indent=4)
    print(json.dumps(asm_schema, indent=4))  # noqa: T201


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", type=str, required=True, help="file to convert")
    parser.add_argument("--vendor", type=str, required=True, help="vendor identifier")
    parser.add_argument(
        "--outfile", type=str, required=False, help="file to write results to"
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""Show CSV file as JSON."""

import argparse
import json
import sys

from allotropy.parser_factory import VENDOR_NAME_LOOKUP
from allotropy.to_allotrope import allotrope_from_io


def main():
    """Main driver."""
    args = parse_args()
    vendor = VENDOR_NAME_LOOKUP[args.vendor]

    if args.infile:
        with open(args.infile, "r") as reader:
            asm_schema = allotrope_from_io(reader, args.infile, vendor)
    else:
        asm_schema = allotrope_from_io(sys.stdin, "<stdin>", vendor)

    print(json.dumps(asm_schema, indent=4))


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", type=str, default=None, help="input file")
    parser.add_argument("--vendor", type=str, default=None, help="vendor identifier")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()

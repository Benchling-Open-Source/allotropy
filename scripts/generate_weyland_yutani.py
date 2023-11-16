#!/usr/bin/env python

# Disable warnings about use of random.random with SHA256.
# ruff: noqa: S311

"""Generate random plates with some formatting gotchas.

Default output is CSV that looks like:

    Weyland-Yutani 470 1879,,,,
    Recorded,2023-10-23:08:21:45,,,
    ,,,,
    ,A,B,C,D
    1,1.67,2.35,4.17,2.75
    2,2.78,2.52,3.23,1.81
    3,0.91,1.35,3.73,1.50
    4,3.34,3.46,3.70,0.77

In order:

-   Machine model and serial number
-   Recording timestamp
-   Blank line
-   4x4 table of readings
-   Blank line

Options:

-   `--checksum`: add footer row with SHA256 checksum
-   `--empty`: create some empty reading cells
-   `--exptime`: specify experiment timestamp
-   `--height`: specify number of rows
-   `--operator`: add a header row with operator name
-   `--out`: specify output file
-   `--seed`: specify random number seed
-   `--serial`: specify machine serial number
-   `--width`: specify number of columns

"""

import argparse
import csv
from datetime import datetime
import hashlib
import random
import sys
from typing import Any

import pytz

CHECKSUM_RANGE = 2**16
MODEL = "Weyland-Yutani 470"
PLATE_HEIGHT = 4
PLATE_WIDTH = 4
SERIAL_NUMBER_RANGE = 1000
MAX_READING = 5.0


def main() -> None:
    """Main driver."""
    args = parse_args()
    head = head_generate(args)
    body = body_generate(args)
    foot = foot_generate(args, body)
    result = csv_normalize([*head, *body, *foot])
    save(args, result)


def body_add_titles(args: argparse.Namespace, readings: list[Any]) -> list[Any]:
    """Make column titles for plate readings."""
    title_row = ["", *[chr(ord("A") + col) for col in range(args.width)]]
    readings = [[str(i + 1), *r] for (i, r) in enumerate(readings)]
    return [title_row, *readings]


def body_calculate_checksum(body: list[Any]) -> str:
    """Calculate SHA256 checksum for body."""
    m = hashlib.sha256()
    for row in body:
        for val in row:
            m.update(bytes(val, "utf-8"))
    digest = int(m.hexdigest(), base=16) % CHECKSUM_RANGE
    return f"{digest:04x}"


def body_empty_readings(args: argparse.Namespace, readings: list[Any]) -> list[Any]:
    """Replace some readings with empty."""
    product = args.width * args.height
    coords = list(range(product))
    coords = random.sample(coords, args.empty)
    for c in coords:
        col = c % args.width
        row = c // args.width
        readings[row][col] = ""
    return readings


def body_generate(args: argparse.Namespace) -> list[Any]:
    """Make body of plate."""
    readings = body_generate_readings(args)
    readings = body_empty_readings(args, readings)
    readings = body_add_titles(args, readings)
    return readings


def body_generate_readings(args: argparse.Namespace) -> list[Any]:
    """Make table of plate readings."""
    return [
        [f"{(random.random() * MAX_READING):.02f}" for _ in range(args.width)]
        for row in range(args.height)
    ]


def csv_normalize(rows: list[Any]) -> list[Any]:
    required = max(len(r) for r in rows)
    for row in rows:
        row.extend([""] * (required - len(row)))
    return rows


def foot_generate(args: argparse.Namespace, body: list[Any]) -> list[Any]:
    """Make foot of plate."""
    result = []
    if args.checksum:
        result.extend(
            [
                [],
                ["Checksum", body_calculate_checksum(body)],
            ]
        )
    return result


def head_generate(args: argparse.Namespace) -> list[Any]:
    """Make head of plate."""
    operator = [["Operator", args.operator]] if args.operator else []
    return [
        [f"{MODEL} {args.serial}"],
        ["Recorded", args.exptime],
        *operator,
        [],
    ]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checksum", action="store_true", default=False, help="include checksum"
    )
    parser.add_argument("--empty", type=int, default=0, help="number of empty readings")
    parser.add_argument("--exptime", type=str, default=None, help="reading date/time")
    parser.add_argument("--height", type=int, default=PLATE_HEIGHT, help="plate height")
    parser.add_argument("--operator", type=str, default=None, help="operator name")
    parser.add_argument("--out", type=str, default=None, help="output file")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed")
    parser.add_argument("--serial", type=str, default=None, help="Reader serial number")
    parser.add_argument("--width", type=int, default=PLATE_WIDTH, help="plate width")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.serial is None:
        args.serial = SERIAL_NUMBER_RANGE + random.randint(1, SERIAL_NUMBER_RANGE - 1)

    if args.exptime is None:
        args.exptime = datetime.now(tz=pytz.utc).strftime("%Y-%m-%d:%H:%M:%S")

    return args


def save(args: argparse.Namespace, rows: list[Any]) -> None:
    """Save as CSV."""
    if args.out is None:
        csv.writer(sys.stdout).writerows(rows)
    else:
        with open(args.out, "w") as writer:
            csv.writer(writer).writerows(rows)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import multiprocessing
import os
import subprocess

import click


def _check_parser(parser: str) -> bool:
    result = subprocess.run(
        [
            "hatch",
            "run",
            "test",
            f"tests/parsers/{parser}/to_allotrope_test.py::TestParser::test_positive_cases",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return "warning" not in result.stdout


def _is_valid_parser(parser: str):
    if parser.startswith("."):
        return False
    if parser.startswith("_"):
        return False
    if parser == "utils":
        return False
    return True


def _check_warn_unread(parser: str | None = None) -> bool:
    parsers = sorted(os.listdir("tests/parsers/"))
    if parser:
        parsers = [parser]

    parsers = [parser for parser in parsers if _is_valid_parser(parser)]

    if len(parsers) > 1:
        with multiprocessing.Pool() as pool:
            results = pool.map(_check_parser, parsers)
    else:
        results = [_check_parser(parsers[0])]

    failing = [
        parser for parser, success in zip(parsers, results, strict=True) if not success
    ]
    if failing:
        print(f"Parsers with unread data warnings: {failing}")
    else:
        print("Success!")

    return not failing


@click.command()
@click.option("--parser", "-p", help="Parser to test, if blank, will test all")
def check_warn_unread(parser: str | None = None) -> bool:
    _check_warn_unread(parser)


if __name__ == "__main__":
    check_warn_unread()

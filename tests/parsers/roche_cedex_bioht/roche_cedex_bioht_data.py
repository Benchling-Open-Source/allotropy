from __future__ import annotations

from io import StringIO

import pandas as pd


def get_data_stream() -> StringIO:
    title = [
        "0",
        "2021-06-01 13:04:06",
        "#ARC-FILE#",
        "1.1a",
        "2021-05-01",
        "2021-06-01",
        "CEDEX BIO HT",
        "620103",
        "6.0.0.1905 (1905)",
        "ADMIN",
    ]

    body = [
        [
            "40",
            "2021-05-20 16:56:51",
            "PPDTEST1",
            "",
            "SAM",
            "        ",
            "GLN2B",
            "        ",
            "mmol/L",
            " ",
            "  2.45",
            "  0.17138",
            "R",
        ],
        [
            "40",
            "2021-05-20 16:55:51",
            "PPDTEST1",
            "",
            "Sample",
            "        ",
            "NH3LB",
            "        ",
            "mmol/L",
            " ",
            "  1.846",
            "0",
            "R",
        ],
        [
            "40",
            "2021-05-20 16:57:51",
            "PPDTEST1",
            "",
            "Sample",
            "        ",
            "ODB",
            "        ",
            "OD",
            " ",
            "  0.17138",
            "0",
            "R",
        ],
    ]
    title_text = "\t".join(title)
    body_text = "\n".join(["\t".join(row) for row in body])
    return StringIO("\n".join([title_text, body_text]))


def get_reader_title() -> pd.Series[str]:
    return pd.Series(
        {
            "row type": 0,
            "data processing time": "2021-06-01 13:04:06",
            "col3": "#ARC-FILE#",
            "col4": "1.1a",
            "col5": "2021-05-01",
            "col6": "2021-06-01",
            "model number": "CEDEX BIO HT",
            "device serial number": 620103,
            "software version": "6.0.0.1905 (1905)",
            "analyst": "ADMIN",
        }
    )


def get_reader_samples() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "row type",
            "measurement time",
            "sample identifier",
            "batch identifier",
            "sample role type",
            "col6",
            "analyte name",
            "col8",
            "concentration unit",
            "flag",
            "concentration value",
            "col12",
            "col13",
            "analyte code",
            "detection kit",
            "detection kit range",
            "original concentration value",
        ],
        data=[
            [
                40,
                "2021-05-20 16:56:51",
                "PPDTEST1",
                "",
                "Sample",
                "        ",
                "glutamine",
                "        ",
                "mmol/L",
                " ",
                2.45,
                0.17138,
                "R",
                "GLN2B",
                "Standard",
                "0.1 - 10.26 mmol/L",
                2.45,
            ],
            [
                40,
                "2021-05-20 16:55:51",
                "PPDTEST1",
                "",
                "Sample",
                "        ",
                "ammonia",
                "        ",
                "mmol/L",
                " ",
                1.846,
                0,
                "R",
                "NH3LB",
                "Low",
                "0.0278 - 1.389 mmol/L",
                1.846,
            ],
            [
                40,
                "2021-05-20 16:57:51",
                "PPDTEST1",
                "",
                "Sample",
                "        ",
                "optical_density",
                "        ",
                "OD",
                " ",
                0.17138,
                0,
                "R",
                "ODB",
                "ODB",
                "ODB",
                0.17138,
            ],
        ],
    )

import json
from pathlib import Path

from allotropy.constants import CHARDET_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file


def main():
    instrument = "agilent_gen5"
    filename = "agile_gen5_multiple_read_modes"
    filepath = f"../tests/parsers/{instrument}/testdata/multi_read_modes/{filename}.txt"

    allotrope_dictionary = allotrope_from_file(
        filepath, Vendor.AGILENT_GEN5, encoding=CHARDET_ENCODING
    )

    output = Path(filepath).with_suffix(".json").name
    with open(output, "w") as fp:
        fp.write(json.dumps(allotrope_dictionary, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()

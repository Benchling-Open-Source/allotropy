import json
from pathlib import Path

from allotropy.constants import CHARDET_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file

def main():
    instrument = "agilent_gen5"
    directory = "multiple_read_modes"
    filename = "jira_cust_8062_bug"
    filepath = f"../tests/parsers/{instrument}/testdata/{directory}/{filename}.txt"
    print(filepath)

    allotropeDictionary = allotrope_from_file(filepath, Vendor.AGILENT_GEN5, encoding=CHARDET_ENCODING)

    output = Path(filepath).with_suffix(".json").name
    print(allotropeDictionary)
    print(output)
    with open(output, "w") as fp:
        fp.write(json.dumps(allotropeDictionary, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
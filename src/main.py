import json
import os

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "roche_cedex_bioht_example05.txt"

current_file_path = os.path.abspath(__file__)
print(current_file_path)

test_filepath = f"../tests/parsers/roche_cedex_bioht/testdata/{file_name}"
allotrope_dict = from_file(test_filepath, Vendor.ROCHE_CEDEX_BIOHT)

print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))  # noqa: T201

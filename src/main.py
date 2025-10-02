# import json

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "pipetting_example.log"

test_filepath = f"../tests/parsers/beckman_coulter_biomek/testdata/{file_name}"
allotrope_dict = from_file(test_filepath, Vendor.BECKMAN_COULTER_BIOMEK)

# print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))

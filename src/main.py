# import json

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "hiac_example_1.xlsx"

test_filepath = f"../tests/parsers/beckman_pharmspec/testdata/{file_name}"
output_filepath = f"../tests/parsers/b/testdata/{file_name.split('.')[0]}.json"
allotrope_dict = from_file(test_filepath, Vendor.BECKMAN_PHARMSPEC)

# print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))
# with open(output_filepath, "w") as f:
#     json.dump(allotrope_dict, f, indent=4, ensure_ascii=False)

# import json

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "Appbio_AbsoluteQ_fluorescence_columns.csv"

test_filepath = f"../tests/parsers/appbio_absolute_q/testdata/{file_name}"
test_output_file = f"{test_filepath.replace('csv', 'json')}"
allotrope_dict = from_file(test_filepath, Vendor.APPBIO_ABSOLUTE_Q)

# print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))
# with open(test_output_file, "w", encoding="utf-8") as output_file:
#     output_file.write(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))

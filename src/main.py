# import json

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "chemometec_nucleoview_example01.csv"

test_filepath = f"../tests/parsers/chemometec_nucleoview/testdata/{file_name}"
test_output_file = f"{test_filepath.replace('.log', '.json')}"
allotrope_dict = from_file(test_filepath, Vendor.CHEMOMETEC_NUCLEOVIEW)

# print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))
# with open(test_output_file, "w", encoding="utf-8") as output_file:
#     output_file.write(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))

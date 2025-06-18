from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "partial_plate_with_empty_values.txt"

test_filepath = f"../tests/parsers/moldev_softmax_pro/testdata/{file_name}"
test_output_file = f"{test_filepath.replace('txt', 'json')}"
allotrope_dict = from_file(test_filepath, Vendor.MOLDEV_SOFTMAX_PRO)

# print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))
# with open(test_output_file, "w", encoding="utf-8") as output_file:
#     output_file.write(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))

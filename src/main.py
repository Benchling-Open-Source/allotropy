from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "nan_columns_test.xlsx"

test_filepath = f"../tests/parsers/thermo_skanit/testdata/{file_name}"
test_output_file = f"{test_filepath.replace('wsp', 'json')}"
allotrope_dict = from_file(test_filepath, Vendor.THERMO_SKANIT)

# print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))
# with open(test_output_file, "w", encoding="utf-8") as output_file:
#     output_file.write(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))

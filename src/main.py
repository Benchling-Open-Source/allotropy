from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "bio-rad_bio-plex_manager_example_01.xml"

test_filepath = f"../tests/parsers/biorad_bioplex_manager/testdata/{file_name}"
test_output_file = f"{test_filepath.replace('wsp', 'json')}"
allotrope_dict = from_file(test_filepath, Vendor.BIORAD_BIOPLEX)

# print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))
# with open(test_output_file, "w", encoding="utf-8") as output_file:
#     output_file.write(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))

import json

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "Luxo HPLC-2023-09-01 07-52-44-04-00.rslt"

test_filepath = f"../tests/parsers/agilent_openlab_cds/testdata/{file_name}"
test_output_file = f"{test_filepath.replace('.rslt', '.json')}"
allotrope_dict = from_file(test_filepath, Vendor.AGILENT_OPENLAB_CDS)

print(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))
with open(test_output_file, "w", encoding="utf-8") as output_file:
    output_file.write(json.dumps(allotrope_dict, indent=4, ensure_ascii=False))

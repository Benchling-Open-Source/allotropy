from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "multi-plate_example01.xlsx"

test_filepath = f"../tests/parsers/thermo_skanit/testdata/{file_name}"
allotrope_dict = from_file(test_filepath, Vendor.THERMO_SKANIT)

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "Thermo_NanoDrop_8000_example01.txt"

test_filepath = f"../tests/parsers/thermo_fisher_nanodrop_8000/testdata/{file_name}"
allotrope_dict = from_file(test_filepath, Vendor.THERMO_FISHER_NANODROP_8000)

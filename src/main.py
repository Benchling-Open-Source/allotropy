from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "thermo_nanodrop_eight_example01.txt"

test_filepath = f"../tests/parsers/thermo_fisher_nanodrop_eight/testdata/{file_name}"
allotrope_dict = from_file(test_filepath, Vendor.THERMO_FISHER_NANODROP_EIGHT)

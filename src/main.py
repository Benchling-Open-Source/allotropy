from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

file_name = "QubitData_sample.csv"

test_filepath = f"../tests/parsers/thermo_fisher_qubit_flex/testdata/{file_name}"
allotrope_dict = from_file(test_filepath, Vendor.THERMO_FISHER_QUBIT_FLEX)

import json

from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file

if __name__ == "__main__":
    filepath = "/Users/yukthiwickramarachchi/allotropy/tests/parsers/perkin_elmer_envision/testdata/PE_Envision_example03.csv"
    asm_schema = allotrope_from_file(filepath, Vendor.PERKIN_ELMER_ENVISION)
    with open("sample.json", "w") as outfile:
        json.dump(asm_schema, outfile)

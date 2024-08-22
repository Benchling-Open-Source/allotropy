from typing import Any

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_one.constants import DISPLAY_NAME
from allotropy.parsers.thermo_fisher_nanodrop_one.thermo_fisher_nanodrop_one_structure import (
    Data,
)
from allotropy.parsers.utils.pandas import read_multisheet_excel
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherNanodropOneParser(VendorParser):
    @property
    def display_name(self) -> str:
        return DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.WORKING_DRAFT

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        contents = read_multisheet_excel(
            named_file_contents.contents,
            engine="calamine",
        )
        data = Data.create(contents)
        return self._get_model(data)

    def _get_model(self, _: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
        )

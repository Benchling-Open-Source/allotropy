from allotropy.allotrope.models.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class PharmSpecParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Beckman PharmSpec"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = create_data(named_file_contents)
        return self._get_mapper(Mapper).map_model(data)

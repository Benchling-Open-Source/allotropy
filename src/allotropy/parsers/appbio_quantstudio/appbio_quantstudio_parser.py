from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import Mapper
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    create_data,
)
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppBioQuantStudioParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "AppBio QuantStudio RT-PCR"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = LinesReader(lines)
        data = create_data(reader, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)

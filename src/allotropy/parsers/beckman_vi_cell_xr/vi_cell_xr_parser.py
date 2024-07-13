from __future__ import annotations

import tempfile
import zipfile

from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellXRReader
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_structure import create_data
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_txt_reader import ViCellXRTXTReader
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser
from allotropy.types import IOType


def remove_style_xml_file(contents: IOType) -> IOType:
    # Removes styles.xml from an xlsx file IO stream. xlsx files produced by VI-Cell XR
    # instrument may have an invalid <fill> tag in their styles.xml file which causes a
    # bug when reading with pandas (via openpyxl library).

    # zipfile only accepts a filename, so write contents to a named temp file.
    tmp = tempfile.NamedTemporaryFile()
    file_contents = contents.read()
    if isinstance(file_contents, str):
        file_contents = file_contents.encode()
    tmp.write(file_contents)

    # Write zip contents to a new file, skipping styles.xml
    new = tempfile.NamedTemporaryFile()
    with zipfile.ZipFile(tmp.name) as zin:
        with zipfile.ZipFile(new.name, "w") as zout:
            for item in zin.infolist():
                if item.filename == "xl/styles.xml":
                    continue
                zout.writestr(item, zin.read(item.filename))

    return open(new.name, "rb")


class ViCellXRParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Beckman Vi-Cell XR"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name

        if filename.endswith("xlsx"):
            contents = remove_style_xml_file(contents)

        reader: ViCellXRTXTReader | ViCellXRReader
        if filename.endswith("txt"):
            reader = ViCellXRTXTReader(named_file_contents)
        else:
            reader = ViCellXRReader(contents)

        data = create_data(reader)

        mapper = Mapper(self.get_asm_converter_name(), self._get_date_time)
        return mapper.map_model(data, filename)

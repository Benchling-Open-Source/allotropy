from __future__ import annotations

import zipfile

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_reader import (
    AppbioAbsoluteQReader,
)
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_structure import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
    Group,
    Well,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppbioAbsoluteQParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "AppBio AbsoluteQ"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AppbioAbsoluteQReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            if named_file_contents.extension == "zip":
                named_file_contents.contents.seek(0)
                with zipfile.ZipFile(named_file_contents.get_bytes_stream()) as zf:
                    return any(name.endswith("_summary.csv") for name in zf.namelist())
            named_file_contents.contents.seek(0)
            raw = named_file_contents.contents.read(8192)
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            if len(lines) < 2:
                return False
            all_cols: set[str] = set()
            for line in lines[:2]:
                all_cols.update(c.strip() for c in line.split(","))
            has_instrument_plate = "Instrument" in all_cols and "Plate" in all_cols
            if has_instrument_plate:
                return bool(all_cols & {"Dye", "Target", "Channels"}) or any(
                    "_target" in c for c in all_cols
                )
            return (
                "Run name" in all_cols and "Target" in all_cols and "Total" in all_cols
            )
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AppbioAbsoluteQReader(named_file_contents)
        wells = Well.create_wells(reader.data)
        groups = Group.create_rows(reader.data)

        return Data(
            create_metadata(
                wells[0].items[0].instrument_identifier,
                named_file_contents.original_file_path,
            ),
            create_measurement_groups(wells),
            calculated_data=create_calculated_data(
                wells, groups, reader.common_columns
            ),
        )

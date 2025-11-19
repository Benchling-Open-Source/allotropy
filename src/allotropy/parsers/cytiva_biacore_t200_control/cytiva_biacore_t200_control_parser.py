import json
from pathlib import Path, PureWindowsPath
import warnings

from allotropy.allotrope.models.adm.binding_affinity_analyzer.wd._2024._12.binding_affinity_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    Data as MapperData,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cytiva_biacore_t200_control import constants
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_data_creator import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_decoder import (
    decode_data,
)
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_structure import (
    Data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.dict_data import DictData
from allotropy.parsers.vendor_parser import VendorParser


class CytivaBiacoreT200ControlParser(VendorParser[MapperData, Model]):
    DISPLAY_NAME = constants.DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "blr"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> MapperData:
        base_data = DictData(decode_data(named_file_contents))
        data = Data.create(base_data)
        mapper_data = MapperData(
            metadata=create_metadata(data, named_file_contents),
            measurement_groups=create_measurement_groups(data),
            calculated_data=create_calculated_data(data),
        )
        try:
            unread = base_data.get_unread_deep()
            original_path = named_file_contents.original_file_path
            # Derive file stem robustly for both POSIX and Windows-style paths
            stem = (
                PureWindowsPath(original_path).stem
                if "\\" in original_path and "/" not in original_path
                else Path(original_path).stem
            )
            out_name = f"{stem}data_unread_2.json"
            with open(out_name, "w", encoding="utf-8") as f:
                json.dump(unread, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Best-effort debug artifact; do not break parsing on failure
            warnings.warn(f"Failed to write unread debug file: {e!s}", stacklevel=1)
        return mapper_data

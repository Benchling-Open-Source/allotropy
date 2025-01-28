from collections import defaultdict

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import SampleRoleType
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import WellItem
from allotropy.parsers.appbio_quantstudio.views import View


class SampleView(View[WellItem]):
    def sort_elements(self, well_items: list[WellItem]) -> dict[str, list[WellItem]]:
        items = defaultdict(list)
        for well_item in well_items:
            items[well_item.sample_identifier].append(well_item)
        return dict(items)


class TargetView(View[WellItem]):
    def sort_elements(self, well_items: list[WellItem]) -> dict[str, list[WellItem]]:
        items = defaultdict(list)
        for well_item in well_items:
            items[well_item.target_dna_description].append(well_item)
        return dict(items)


class TargetRoleView(View[WellItem]):
    def sort_elements(self, well_items: list[WellItem]) -> dict[str, list[WellItem]]:
        items = defaultdict(list)
        for well_item in well_items:
            if well_item.sample_role_type == SampleRoleType.standard_sample_role:
                items[well_item.target_dna_description].append(well_item)
        return dict(items)

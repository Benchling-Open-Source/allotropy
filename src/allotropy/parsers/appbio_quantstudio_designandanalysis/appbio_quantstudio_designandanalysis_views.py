from collections import defaultdict

from allotropy.parsers.appbio_quantstudio.views import View
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    SAMPLE_ROLE_TYPES_MAP,
    WellItem,
)
from allotropy.parsers.utils.values import assert_not_none


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
        standard_sample_role_type = assert_not_none(
            SAMPLE_ROLE_TYPES_MAP.get("STANDARD"),
            msg="Unable to get sample role type map for STANDARD value.",
        )

        items = defaultdict(list)
        for well_item in well_items:
            if well_item.sample_role_type == standard_sample_role_type:
                items[well_item.target_dna_description].append(well_item)
        return dict(items)

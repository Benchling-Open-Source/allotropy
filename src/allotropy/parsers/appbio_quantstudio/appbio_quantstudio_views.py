from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import WellItem
from allotropy.parsers.appbio_quantstudio.views import View


class SampleView(View[WellItem]):
    def sort_elements(self, well_items: list[WellItem]) -> dict[str, list[WellItem]]:
        items: dict[str, list[WellItem]] = {}
        for well_item in well_items:
            if well_item.sample_identifier not in items:
                items[well_item.sample_identifier] = []
            items[well_item.sample_identifier].append(well_item)
        return items


class TargetView(View[WellItem]):
    def sort_elements(self, well_items: list[WellItem]) -> dict[str, list[WellItem]]:
        items: dict[str, list[WellItem]] = {}
        for well_item in well_items:
            if well_item.target_dna_description not in items:
                items[well_item.target_dna_description] = []
            items[well_item.target_dna_description].append(well_item)
        return items


class TargetRoleView(View[WellItem]):
    def sort_elements(self, well_items: list[WellItem]) -> dict[str, list[WellItem]]:
        items: dict[str, list[WellItem]] = {}
        for well_item in well_items:
            if well_item.sample_role_type == "STANDARD":
                if well_item.target_dna_description not in items:
                    items[well_item.target_dna_description] = []
                items[well_item.target_dna_description].append(well_item)
        return items

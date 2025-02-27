from __future__ import annotations

from collections import defaultdict

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class BlankRoleTypeView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="sample_role_type", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            sample_role_type = element.get_str("sample_role_type")
            if sample_role_type == SampleRoleType.blank_role.name:
                items[str(sample_role_type)].append(element)
        return dict(items)


class CorrectedView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="corrected_value", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if corrected_value := element.get_float_or_none("corrected_value"):
                items[str(corrected_value)].append(element)
        return dict(items)

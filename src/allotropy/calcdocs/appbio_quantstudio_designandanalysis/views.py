from collections import defaultdict

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class SampleView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="sample_id", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if sample_identifier := element.get_str("sample_identifier"):
                items[str(sample_identifier)].append(element)
        return dict(items)


class TargetView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="target_dna", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if target_dna_description := element.get_str("target_dna_description"):
                items[str(target_dna_description)].append(element)
        return dict(items)


class UuidView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="uuid", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if uuid := element.get_str("uuid"):
                items[str(uuid)].append(element)
        return dict(items)


class TargetRoleView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="target_dna", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if target_dna := element.get_str_or_none("target_dna_description"):
                if element.get_str("sample_role_type") == "standard sample role":
                    items[str(target_dna)].append(element)
        return dict(items)

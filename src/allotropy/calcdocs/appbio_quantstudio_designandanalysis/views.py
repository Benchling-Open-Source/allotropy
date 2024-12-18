from collections import defaultdict

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class SampleView(View):
    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if sample_identifier := element.get("sample_identifier"):
                items[str(sample_identifier)].append(element)
        return dict(items)


class TargetView(View):
    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if target_dna_description := element.get("target_dna_description"):
                items[str(target_dna_description)].append(element)
        return dict(items)


class UuidView(View):
    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if uuid := element.get("uuid"):
                items[str(uuid)].append(element)
        return dict(items)


class TargetRoleView(View):
    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if target_dna_description := element.get("target_dna_description"):
                if element.get("sample role type") == "standard sample role":
                    items[str(target_dna_description)].append(element)
        return dict(items)

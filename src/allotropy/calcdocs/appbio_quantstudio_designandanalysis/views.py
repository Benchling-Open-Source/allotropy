from __future__ import annotations

from collections import defaultdict

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class ViewWithReference(View):
    def __init__(
        self,
        name: str,
        sub_view: ViewWithReference | None,
        reference: str | None = None,
    ):
        super().__init__(name, sub_view)
        self.reference = reference

    def filter_keys(self, keys: dict[str, str]) -> dict[str, str]:
        filtered_keys = super().filter_keys(keys)
        if self.reference is not None and self.name in filtered_keys:
            filtered_keys[self.name] = self.reference
        return filtered_keys


class SampleView(ViewWithReference):
    def __init__(
        self,
        sub_view: ViewWithReference | None = None,
        reference: str | None = None,
    ):
        super().__init__(name="sample_id", sub_view=sub_view, reference=reference)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if sample_identifier := element.get_str("sample_identifier"):
                items[str(sample_identifier)].append(element)
        return dict(items)


class TargetView(ViewWithReference):
    def __init__(
        self,
        sub_view: ViewWithReference | None = None,
        reference: str | None = None,
        blacklist: list[str] | None = None,
    ):
        super().__init__(name="target_dna", sub_view=sub_view, reference=reference)
        self.blacklist = blacklist

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if target_dna_description := element.get_str("target_dna_description"):
                if self.blacklist is None or target_dna_description not in self.blacklist:
                    items[str(target_dna_description)].append(element)
        return dict(items)


class UuidView(ViewWithReference):
    def __init__(self, sub_view: ViewWithReference | None = None):
        super().__init__(name="uuid", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if uuid := element.get_str("uuid"):
                items[str(uuid)].append(element)
        return dict(items)


class TargetRoleView(ViewWithReference):
    def __init__(self, sub_view: ViewWithReference | None = None):
        super().__init__(name="target_dna", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if target_dna := element.get_str_or_none("target_dna_description"):
                if element.get_str("sample_role_type") == "standard sample role":
                    items[str(target_dna)].append(element)
        return dict(items)

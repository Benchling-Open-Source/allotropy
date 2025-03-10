from __future__ import annotations

from collections import defaultdict

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import SampleRoleType
from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import Keys, View, ViewData


class ViewWithReference(View):
    def __init__(
        self,
        name: str,
        sub_view: View | None,
        reference: str | None = None,
    ):
        super().__init__(name, sub_view)
        self.reference = reference

    def filter_keys(self, keys: Keys) -> Keys:
        filtered_keys = super().filter_keys(keys)
        if self.reference is not None and filtered_keys.get_or_none(self.name):
            return filtered_keys.overwrite(self.name, self.reference)
        return filtered_keys


class SampleView(ViewWithReference):
    def __init__(self, sub_view: View | None = None, reference: str | None = None):
        super().__init__(name="sample_id", sub_view=sub_view, reference=reference)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if sample_identifier := element.get_str("sample_identifier"):
                items[sample_identifier].append(element)
        return dict(items)


class TargetView(ViewWithReference):
    def __init__(
        self,
        sub_view: View | None = None,
        is_reference: bool = False,  # noqa: FBT001 FBT002
        reference: str | None = None,
        blacklist: list[str] | None = None,
    ):
        super().__init__(name="target_dna", sub_view=sub_view, reference=reference)
        self.is_reference = is_reference
        self.blacklist = blacklist

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if target_dna := element.get_str("target_dna_description"):
                if self.blacklist is None or target_dna not in self.blacklist:
                    items[target_dna].append(element)
        return dict(items)

    def filter_keys(self, keys: Keys) -> Keys:
        if self.is_reference and self.reference is None:
            return Keys()
        return super().filter_keys(keys)

    def apply(self, elements: list[Element]) -> ViewData:
        if self.is_reference and self.reference is None:
            return ViewData(view=self, name=self.name, data={})
        return super().apply(elements)


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
            if target_dna := element.get_str("target_dna_description"):
                sample_role_type = element.get_str("sample_role_type")
                if sample_role_type == SampleRoleType.standard_sample_role:
                    items[target_dna].append(element)
        return dict(items)

from collections import defaultdict

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class AssayIdentifierView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="assay_identifier", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            assay_identifier = element.get_str("assay_identifier")
            items[assay_identifier].append(element)
        return dict(items)


class SampleIdentifierView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="sample_identifier", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            sample_identifier = element.get_str("sample_identifier")
            items[sample_identifier].append(element)
        return dict(items)


class WellPlateIdentifierView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="well_plate_identifier", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            well_plate_identifier = element.get_str("well_plate_identifier")
            items[well_plate_identifier].append(element)
        return dict(items)


class LocationIdentifierView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="location_identifier", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            location_identifier = element.get_str("location_identifier")
            items[location_identifier].append(element)
        return dict(items)

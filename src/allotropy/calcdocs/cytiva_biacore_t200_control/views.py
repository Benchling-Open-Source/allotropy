from __future__ import annotations

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class ReportPointDataView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="report_point_data", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        return {element.uuid: [element] for element in elements}

from collections import defaultdict

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class PosView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="pos", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if pos := element.get_float_or_none("pos"):
                items[str(pos)].append(element)
        return dict(items)

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.perkin_elmer_envision.extractor import (
    PerkinElmerEnvisionExtractor,
)
from allotropy.calcdocs.view import View, ViewData
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    CalculatedPlate,
    PlateList,
)


class PosView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="pos", sub_view=sub_view)

    def sort_elements(self, _: list[Element]) -> dict[str, list[Element]]:
        return {}

    def special_apply(
        self, plate_list: PlateList, calculated_plate: CalculatedPlate
    ) -> ViewData:
        return ViewData(
            view=self,
            name=self.name,
            data={
                calculated_result.pos: [
                    PerkinElmerEnvisionExtractor.to_element_with_extra_data(
                        source_result,
                        extra_data={"calc value": calculated_result.value},
                    )
                    for source_result in source_results
                ]
                for calculated_result, source_results in calculated_plate.get_result_and_sources(
                    plate_list
                )
            },
        )

from allotropy.calcdocs.extractor import Element, Extractor
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    CalculatedPlate,
    CalculatedPlateInfo,
    CalculatedResult,
    PlateInfo,
    PlateList,
    Result,
    ResultPlate,
    ResultPlateInfo,
)


class PerkinElmerEnvisionExtractor(Extractor[Result | CalculatedResult]):
    @classmethod
    def to_element(cls, result: Result | CalculatedResult) -> Element:
        return Element(
            uuid=result.uuid,
            data={
                "col": result.col,
                "row": result.row,
                "value": result.value,
            },
        )

    @classmethod
    def extend_plate_element(cls, plate_info: PlateInfo, element: Element) -> Element:
        element.data["number"] = plate_info.number
        element.data["barcode"] = plate_info.barcode
        element.data["measurement_time"] = plate_info.measurement_time
        element.data["measured_height"] = plate_info.measured_height
        element.data["chamber_temp_start"] = plate_info.chamber_temperature_at_start
        return element

    @classmethod
    def extend_result_plate_element(
        cls, plate_info: ResultPlateInfo, element: Element
    ) -> Element:
        element.data["label"] = plate_info.label
        element.data["measinfo"] = plate_info.measinfo
        element.data["emission_filter_id"] = plate_info.emission_filter_id
        return cls.extend_plate_element(plate_info, element)

    @classmethod
    def extend_calculated_plate_element(
        cls, plate_info: CalculatedPlateInfo, element: Element
    ) -> Element:
        element.data["formula"] = plate_info.formula
        element.data["name"] = plate_info.name
        return cls.extend_plate_element(plate_info, element)

    @classmethod
    def to_result_plate_element(cls, result_plate: ResultPlate) -> list[Element]:
        return [
            cls.extend_result_plate_element(
                result_plate.plate_info, cls.to_element(result)
            )
            for result in result_plate.results
        ]

    @classmethod
    def to_calculated_plate_element(
        cls, calculated_plate: CalculatedPlate
    ) -> list[Element]:
        return [
            cls.extend_calculated_plate_element(
                calculated_plate.plate_info, cls.to_element(result)
            )
            for result in calculated_plate.results
        ]

    @classmethod
    def get_elements_from_plate_list(cls, plate_list: PlateList) -> list[Element]:
        result_elements = []
        for result_plate in plate_list.results:
            result_elements += cls.to_result_plate_element(result_plate)

        calculated_elements = []
        for calculated_plate in plate_list.calculated:
            calculated_elements += cls.to_calculated_plate_element(calculated_plate)

        return result_elements + calculated_elements

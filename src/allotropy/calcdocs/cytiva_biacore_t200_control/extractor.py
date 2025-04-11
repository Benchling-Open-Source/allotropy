from allotropy.calcdocs.extractor import Element, Extractor
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_structure import (
    ReportPointData,
    SampleData,
)


class CytivaBiacoreExtractor(Extractor[ReportPointData]):
    @classmethod
    def sample_data_to_elements(cls, sample_data: SampleData) -> list[Element]:
        elements = []
        for measurements_data in sample_data.measurements.values():
            for measurement in measurements_data:
                if measurement.report_point_data is None:
                    continue
                elements.extend(cls.get_elements(measurement.report_point_data))
        return elements

    @classmethod
    def get_elements(cls, report_points: list[ReportPointData]) -> list[Element]:
        return [cls.to_element(report_point) for report_point in report_points]

    @classmethod
    def to_element(cls, report_point: ReportPointData) -> Element:
        return Element(
            uuid=report_point.identifier,
            data={
                "absolute_resonance": report_point.absolute_resonance,
                "min_resonance": report_point.min_resonance,
                "max_resonance": report_point.max_resonance,
                "lrsd": report_point.lrsd,
                "slope": report_point.slope,
                "sd": report_point.sd,
            },
        )

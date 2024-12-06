from __future__ import annotations

from dataclasses import dataclass

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass
class StaticDocs:
    chromatography_serial_num: str
    column_inner_diameter: float
    chromatography_chemistry_type: str
    chromatography_particle_size: float
    injection_identifier: str
    injection_time: str
    autosampler_injection_volume_setting: float
    sample_identifier: str
    batch_identifier: str

    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        curve: StrictXmlElement,
        results: StrictXmlElement,
    ) -> StaticDocs:
        column_type_data = handler.get_column_type_data()
        inj_result = cls.__filter_result_criteria(results, keyword="Sample volume")
        sample_result = cls.__filter_result_criteria(results, keyword="Sample_ID")

        return StaticDocs(
            chromatography_serial_num=column_type_data.recursive_find(
                ["ColumnType", "Hardware", "ArticleNumber"]
            ).get_text(),
            column_inner_diameter=column_type_data.recursive_find(
                ["ColumnType", "Hardware", "Diameter"]
            ).get_float("column inner diameter"),
            chromatography_chemistry_type=column_type_data.recursive_find(
                ["ColumnType", "Media", "TechniqueName"]
            ).get_text(),
            chromatography_particle_size=column_type_data.recursive_find(
                ["ColumnType", "Media", "AverageParticleDiameter"]
            ).get_float("chromatography particle size"),
            injection_identifier=random_uuid_str(),
            injection_time=curve.find("MethodStartTime").get_text(),
            autosampler_injection_volume_setting=inj_result.find("Keyword2").get_float(
                "autosampler injection volume setting"
            ),
            sample_identifier=sample_result.find("Keyword2").get_text(),
            batch_identifier=results.find("BatchId").get_text(),
        )

    @classmethod
    def __filter_result_criteria(
        cls, results: StrictXmlElement, keyword: str
    ) -> StrictXmlElement:
        for result_criteria in results.find("ResultSearchCriterias").findall(
            "ResultSearchCriteria"
        ):
            if result_criteria.find("Keyword1").get_text() == keyword:
                return result_criteria
        msg = f"Unable to find result criteria with keyword 1 '{keyword}'"
        raise AllotropeConversionError(msg)

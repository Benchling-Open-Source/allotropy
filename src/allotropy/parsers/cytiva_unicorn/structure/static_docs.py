from __future__ import annotations

from dataclasses import dataclass

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass
class StaticDocs:
    chromatography_serial_num: str | None
    column_inner_diameter: float | None
    chromatography_chemistry_type: str | None
    chromatography_particle_size: float | None
    injection_identifier: str
    injection_time: str
    autosampler_injection_volume_setting: float
    sample_identifier: str
    batch_identifier: str | None

    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        curve: StrictXmlElement,
        results: StrictXmlElement,
    ) -> StaticDocs:
        column_type_data = handler.get_column_type_data()
        autosampler_injection_volume_setting = NEGATIVE_ZERO
        try:
            inj_result = cls.__filter_result_criteria(results, keyword="Sample volume")
            autosampler_injection_volume_setting = inj_result.find(
                "Keyword2"
            ).get_float("autosampler injection volume setting")
        except Exception:
            pass

        sample_identifier = NOT_APPLICABLE
        try:
            sample_result = cls.__filter_result_criteria(results, keyword="Sample_ID")
            sample_identifier = sample_result.find("Keyword2").get_text()
        except Exception:
            pass

        article_number = column_type_data.recursive_find_or_none(
            ["ColumnType", "Hardware", "ArticleNumber"]
        )

        diameter = column_type_data.recursive_find_or_none(
            ["ColumnType", "Hardware", "Diameter"]
        )

        technique_name = column_type_data.recursive_find_or_none(
            ["ColumnType", "Media", "TechniqueName"]
        )

        avg_particle_diameter = column_type_data.recursive_find_or_none(
            ["ColumnType", "Media", "AverageParticleDiameter"]
        )

        batch_id = results.find_or_none("BatchId")

        return StaticDocs(
            chromatography_serial_num=(
                article_number.get_text() if article_number is not None else None
            ),
            column_inner_diameter=(
                diameter.get_float("column inner diameter")
                if diameter is not None
                else None
            ),
            chromatography_chemistry_type=(
                technique_name.get_text() if technique_name is not None else None
            ),
            chromatography_particle_size=(
                avg_particle_diameter.get_float("chromatography particle size")
                if avg_particle_diameter is not None
                else None
            ),
            injection_identifier=random_uuid_str(),
            injection_time=curve.find("MethodStartTime").get_text(),
            autosampler_injection_volume_setting=autosampler_injection_volume_setting,
            sample_identifier=sample_identifier,
            batch_identifier=(batch_id.get_text() if batch_id is not None else None),
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

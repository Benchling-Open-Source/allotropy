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
    sample_volume_2: float | None
    sample_volume_3: float | None
    sample_identifier: str
    sample_identifier_2: str | None
    sample_identifier_3: str | None
    batch_identifier: str | None
    start_time: str | None
    void_volume: float | None
    flow_rate: float | None

    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        curve: StrictXmlElement,
        results: StrictXmlElement,
        analysis_settings: StrictXmlElement | None,
    ) -> StaticDocs:
        column_type_data = handler.get_column_type_data()
        autosampler_injection_volume_setting = NEGATIVE_ZERO
        try:
            inj_result = cls.__filter_result_criteria(results, keyword="Sample volume")
            autosampler_injection_volume_setting = inj_result.find(
                "Keyword2"
            ).get_float("Sample volume")
        except AllotropeConversionError:
            pass

        sample_volume_2 = None
        try:
            inj_result = cls.__filter_result_criteria(
                results, keyword="Sample volume_2"
            )
            sample_volume_2 = inj_result.find("Keyword2").get_float("sample_volume_2")
        except AllotropeConversionError:
            pass
        sample_volume_3 = None
        try:
            inj_result = cls.__filter_result_criteria(
                results, keyword="Sample volume_3"
            )
            sample_volume_3 = inj_result.find("Keyword2").get_float("Sample volume_3")
        except AllotropeConversionError:
            pass

        sample_identifier = NOT_APPLICABLE
        try:
            sample_result = cls.__filter_result_criteria(results, keyword="Sample_ID")
            sample_identifier = sample_result.find("Keyword2").get_text(
                "Sample_ID keyword2"
            )
        except AllotropeConversionError:
            pass

        sample_identifier_2 = None
        try:
            sample_result = cls.__filter_result_criteria(results, keyword="Sample_ID_2")
            sample_identifier = sample_result.find("Keyword2").get_text(
                "Sample_ID_2 keyword2"
            )
        except AllotropeConversionError:
            pass

        sample_identifier_3 = None
        try:
            sample_result = cls.__filter_result_criteria(results, keyword="Sample_ID_3")
            sample_identifier = sample_result.find("Keyword2").get_text(
                "Sample_ID_3 keyword2"
            )
        except AllotropeConversionError:
            pass

        flow_rate = None
        try:
            flow_rate_result = cls.__filter_result_criteria(
                results, keyword="Flow rate"
            )
            flow_rate = flow_rate_result.find("Keyword2").get_float("Flow rate")
        except AllotropeConversionError:
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

        void_volume = None
        if analysis_settings:
            if chromatogram_analysis_settings := analysis_settings.parse_text_or_none():
                void_volume = chromatogram_analysis_settings.recursive_find_or_none(
                    ["IntegrationSettings", "ColumnProperties", "ColumnVolume"]
                )

        return StaticDocs(
            chromatography_serial_num=(
                article_number.get_text_or_none()
                if article_number is not None
                else None
            ),
            column_inner_diameter=(
                diameter.get_float("column inner diameter") * 10
                if diameter is not None
                else None
            ),
            chromatography_chemistry_type=(
                technique_name.get_text_or_none()
                if technique_name is not None
                else None
            ),
            chromatography_particle_size=(
                avg_particle_diameter.get_float("chromatography particle size")
                if avg_particle_diameter is not None
                else None
            ),
            injection_identifier=random_uuid_str(),
            injection_time=curve.find("MethodStartTime").get_text("MethodStartTime"),
            autosampler_injection_volume_setting=autosampler_injection_volume_setting,
            sample_volume_2=sample_volume_2,
            sample_volume_3=sample_volume_3,
            sample_identifier=sample_identifier,
            sample_identifier_2=sample_identifier_2,
            sample_identifier_3=sample_identifier_3,
            batch_identifier=(
                batch_id.get_text_or_none() if batch_id is not None else None
            ),
            start_time=curve.get_sub_text_or_none("MethodStartTime"),
            void_volume=(
                void_volume.get_float_or_none() if void_volume is not None else None
            ),
            flow_rate=flow_rate,
        )

    @classmethod
    def __filter_result_criteria(
        cls, results: StrictXmlElement, keyword: str
    ) -> StrictXmlElement:
        for result_criteria in results.find("ResultSearchCriterias").findall(
            "ResultSearchCriteria"
        ):
            if result_criteria.find("Keyword1").get_text_or_none() == keyword:
                return result_criteria
        msg = f"Unable to find result criteria with keyword 1 '{keyword}'"
        raise AllotropeConversionError(msg)

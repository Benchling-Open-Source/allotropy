from __future__ import annotations

from dataclasses import dataclass

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    ChromatographyDoc,
    InjectionDoc,
    SampleDoc,
)
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
    chromatography_doc: ChromatographyDoc
    injection_doc: InjectionDoc
    sample_doc: SampleDoc

    @classmethod
    def create(
        cls,
        handler: UnicornZipHandler,
        curve: StrictXmlElement,
        results: StrictXmlElement,
    ) -> StaticDocs:
        return StaticDocs(
            chromatography_doc=cls.get_chromatography_doc(handler),
            injection_doc=cls.get_injection_doc(curve, results),
            sample_doc=cls.get_sample_doc(results),
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

    @classmethod
    def get_chromatography_doc(cls, handler: UnicornZipHandler) -> ChromatographyDoc:
        column_type_data = handler.get_column_type_data()
        return ChromatographyDoc(
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
        )

    @classmethod
    def get_injection_doc(
        cls,
        curve_element: StrictXmlElement,
        results: StrictXmlElement,
    ) -> InjectionDoc:
        result = cls.__filter_result_criteria(results, keyword="Sample volume")
        return InjectionDoc(
            injection_identifier=random_uuid_str(),
            injection_time=curve_element.find("MethodStartTime").get_text(),
            autosampler_injection_volume_setting=result.find("Keyword2").get_float(
                "autosampler injection volume setting"
            ),
        )

    @classmethod
    def get_sample_doc(cls, results: StrictXmlElement) -> SampleDoc:
        result = cls.__filter_result_criteria(results, keyword="Sample_ID")
        return SampleDoc(
            sample_identifier=result.find("Keyword2").get_text(),
            batch_identifier=results.find("BatchId").get_text(),
        )

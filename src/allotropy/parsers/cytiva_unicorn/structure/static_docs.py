from __future__ import annotations

from dataclasses import dataclass

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    ChromatographyDoc,
    InjectionDoc,
    SampleDoc,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float


@dataclass
class StaticDocs:
    chromatography_doc: ChromatographyDoc
    injection_doc: InjectionDoc
    sample_doc: SampleDoc

    @classmethod
    def create(
        cls, handler: UnicornZipHandler, curve: StrictElement, results: StrictElement
    ) -> StaticDocs:
        return StaticDocs(
            chromatography_doc=cls.get_chromatography_doc(handler),
            injection_doc=cls.get_injection_doc(curve, results),
            sample_doc=cls.get_sample_doc(results),
        )

    @classmethod
    def __filter_result_criteria(
        cls, results: StrictElement, keyword: str
    ) -> StrictElement:
        for result_criteria in results.find("ResultSearchCriterias").findall(
            "ResultSearchCriteria"
        ):
            if result_criteria.find_text(["Keyword1"]) == keyword:
                return result_criteria
        msg = f"Unable to find result criteria with keyword 1 '{keyword}'"
        raise AllotropeConversionError(msg)

    @classmethod
    def get_chromatography_doc(cls, handler: UnicornZipHandler) -> ChromatographyDoc:
        column_type_data = handler.get_column_type_data()
        return ChromatographyDoc(
            chromatography_serial_num=column_type_data.find_text(
                ["ColumnType", "Hardware", "ArticleNumber"]
            ),
            column_inner_diameter=try_float(
                column_type_data.find_text(["ColumnType", "Hardware", "Diameter"]),
                "column inner diameter",
            ),
            chromatography_chemistry_type=column_type_data.find_text(
                ["ColumnType", "Media", "TechniqueName"]
            ),
            chromatography_particle_size=try_float(
                column_type_data.find_text(
                    ["ColumnType", "Media", "AverageParticleDiameter"]
                ),
                "chromatography particle size",
            ),
        )

    @classmethod
    def get_injection_doc(
        cls,
        curve_element: StrictElement,
        results: StrictElement,
    ) -> InjectionDoc:
        result = cls.__filter_result_criteria(results, keyword="Sample volume")
        return InjectionDoc(
            injection_identifier=random_uuid_str(),
            injection_time=curve_element.find_text(["MethodStartTime"]),
            autosampler_injection_volume_setting=try_float(
                result.find_text(["Keyword2"]),
                "autosampler injection volume setting",
            ),
        )

    @classmethod
    def get_sample_doc(cls, results: StrictElement) -> SampleDoc:
        result = cls.__filter_result_criteria(results, keyword="Sample_ID")
        return SampleDoc(
            sample_identifier=result.find_text(["Keyword2"]),
            batch_identifier=results.find_text(["BatchId"]),
        )

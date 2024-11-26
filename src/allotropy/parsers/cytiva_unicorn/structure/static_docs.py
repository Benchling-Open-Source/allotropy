from __future__ import annotations

from dataclasses import dataclass

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    ChromatographyDoc,
    InjectionDoc,
    SampleDoc,
)
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    StrictElement,
    UnicornFileHandler,
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
        cls, handler: UnicornFileHandler, curve: StrictElement, results: StrictElement
    ) -> StaticDocs:
        return StaticDocs(
            chromatography_doc=cls.get_chromatography_doc(handler),
            injection_doc=cls.get_injection_doc(handler, curve, results),
            sample_doc=cls.get_sample_doc(handler, results),
        )

    @classmethod
    def get_chromatography_doc(cls, handler: UnicornFileHandler) -> ChromatographyDoc:
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
        handler: UnicornFileHandler,
        curve_element: StrictElement,
        results: StrictElement,
    ) -> InjectionDoc:
        result = handler.filter_result_criteria(results, keyword="Sample volume")
        return InjectionDoc(
            injection_identifier=random_uuid_str(),
            injection_time=curve_element.find_text(["MethodStartTime"]),
            autosampler_injection_volume_setting=try_float(
                result.find_text(["Keyword2"]),
                "autosampler injection volume setting",
            ),
        )

    @classmethod
    def get_sample_doc(
        cls, handler: UnicornFileHandler, results: StrictElement
    ) -> SampleDoc:
        result = handler.filter_result_criteria(results, keyword="Sample_ID")
        return SampleDoc(
            sample_identifier=result.find_text(["Keyword2"]),
            batch_identifier=results.find_text(["BatchId"]),
        )

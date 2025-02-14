from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    MeasurementGroup,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.absorbance import (
    AbsorbanceMeasurement1,
    AbsorbanceMeasurement2,
    AbsorbanceMeasurement3,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.concentration import (
    ConcentrationMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.conductivity import (
    ConductivityMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.flow import (
    FlowMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.ph import (
    PhMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.pressure import (
    PressureMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.temperature import (
    TemperatureMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)


def create_measurement_groups(
    handler: UnicornZipHandler, results: StrictXmlElement
) -> list[MeasurementGroup]:
    chrom_1 = handler.get_chrom_1()
    analysis_settings = chrom_1.find_or_none("AnalysisSettings")
    curves = chrom_1.find("Curves")
    elements = curves.findall("Curve")

    static_docs = StaticDocs.create(
        handler, curves.find("Curve"), results, analysis_settings
    )
    measurements = [
        AbsorbanceMeasurement1.create_or_none(handler, elements, static_docs),
        AbsorbanceMeasurement2.create_or_none(handler, elements, static_docs),
        AbsorbanceMeasurement3.create_or_none(handler, elements, static_docs),
        ConductivityMeasurement.create_or_none(handler, elements, static_docs),
        PhMeasurement.create_or_none(handler, elements, static_docs),
        ConcentrationMeasurement.create_or_none(handler, elements, static_docs),
        PressureMeasurement.create_or_none(handler, elements, static_docs),
        FlowMeasurement.create_or_none(handler, elements, static_docs),
        TemperatureMeasurement.create_or_none(handler, elements, static_docs),
    ]

    return [
        MeasurementGroup(
            measurements=[measurement for measurement in measurements if measurement],
        )
    ]

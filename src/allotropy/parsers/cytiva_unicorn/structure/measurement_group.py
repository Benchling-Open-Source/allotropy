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
    curves = chrom_1.find("Curves")
    elements = curves.findall("Curve")

    static_docs = StaticDocs.create(handler, curves.find("Curve"), results)

    return [
        MeasurementGroup(
            measurements=[
                AbsorbanceMeasurement1.create(handler, elements, static_docs),
                AbsorbanceMeasurement2.create(handler, elements, static_docs),
                AbsorbanceMeasurement3.create(handler, elements, static_docs),
                ConductivityMeasurement.create(handler, elements, static_docs),
                PhMeasurement.create(handler, elements, static_docs),
                ConcentrationMeasurement.create(handler, elements, static_docs),
                PressureMeasurement.create(handler, elements, static_docs),
                FlowMeasurement.create(handler, elements, static_docs),
                TemperatureMeasurement.create(handler, elements, static_docs),
            ]
        )
    ]

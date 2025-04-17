import re

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Fraction,
    Log,
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
    event_curves = chrom_1.find_or_none("EventCurves")
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
            fractions=create_fractions(event_curves) if event_curves else None,
            logs=create_logs(event_curves) if event_curves else None,
        )
    ]


def create_fractions(event_curves: StrictXmlElement) -> list[Fraction]:
    event_curve_fraction = None
    for event_curve in event_curves.findall("EventCurve"):
        if event_curve.get_attr_or_none("EventCurveType") == "Fraction":
            event_curve_fraction = event_curve
            break

    if event_curve_fraction is None:
        return []

    if events := event_curve_fraction.find_or_none("Events"):
        return [
            Fraction(
                index=f"Fraction Event {idx}",
                fraction_role=event.get_sub_text_or_none("EventText"),
                field_type=event.get_attr_or_none("EventType"),
                retention_time=(
                    None
                    if (t_min := event.get_sub_float_or_none("EventTime")) is None
                    else t_min * 60
                ),
                retention_volume=event.get_sub_float_or_none("EventVolume"),
            )
            for idx, event in enumerate(events.findall("Event"), start=1)
            if event.get_attr_or_none("EventType") in ["Fraction", "Method"]
        ]

    return []


def create_logs(event_curves: StrictXmlElement) -> list[Log]:
    event_curve_logs = None
    for event_curve in event_curves.findall("EventCurve"):
        if event_curve.get_attr_or_none("EventCurveType") == "Logbook":
            event_curve_logs = event_curve
            break

    if event_curve_logs is None:
        return []

    if events := event_curve_logs.find_or_none("Events"):
        logs, method_id = [], None

        for idx, event in enumerate(events.findall("Event"), start=1):
            if event.get_attr_or_none("EventType") not in [
                "System",
                "Method",
                "Manual",
            ]:
                continue

            event_text = event.get_sub_text_or_none("EventText")
            if event_text is None:
                continue

            event_subtype = event.get_attr_or_none("EventSubType")
            if event_subtype == "BlockStart":
                regex = r"Phase (.+) \(Issued\) \(Processing\) \(Completed\)"
                if res := re.match(regex, event_text):
                    method_id = res.group(1)

            logs.append(
                Log(
                    index=f"Run Log Event {idx}",
                    log_entry=event_text,
                    method_identifier=method_id,
                    retention_time=(
                        None
                        if (t_min := event.get_sub_float_or_none("EventTime")) is None
                        else t_min * 60
                    ),
                    retention_volume=event.get_sub_float_or_none("EventVolume"),
                )
            )

            if event_subtype == "BlockEnd" and event_text.startswith("End Phase"):
                method_id = None

    return logs

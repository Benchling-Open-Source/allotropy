from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCubeComponent,
    DeviceControlDoc,
    Measurement,
    MeasurementGroup,
)
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    StrictElement,
    UnicornFileHandler,
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
from allotropy.parsers.cytiva_unicorn.structure.measurements.generic import (
    UnicornMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.ph import (
    PhMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.measurements.pressure import (
    PressureMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def create_measurement_groups(
    handler: UnicornFileHandler, results: StrictElement
) -> list[MeasurementGroup]:
    chrom_1 = handler.get_chrom_1()
    curves = chrom_1.find("Curves")
    elements = curves.findall("Curve")

    static_docs = StaticDocs.create(handler, curves.find("Curve"), results)

    temperature_profile_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="temperature",
        unit="degC",
    )

    temperature_profile_data_cube = handler.filter_curve(elements, r"^Cond temp$")

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
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            temperature_profile_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                temperature_profile_data_cube,
                                temperature_profile_component,
                            ),
                        ),
                    ],
                ),
            ]
        )
    ]

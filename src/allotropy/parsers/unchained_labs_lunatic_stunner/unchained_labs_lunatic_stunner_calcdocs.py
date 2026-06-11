from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    MeasurementGroup,
)
from allotropy.calcdocs import (
    build_calc_docs,
    CalcDoc,
    FieldView,
    Measurement as CalcMeasurement,
    Node,
    UuidView,
)
from allotropy.calcdocs.unchained_labs_lunatic_stunner.extractor import LunaticExtractor
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)

_ABSORBANCE = CalcMeasurement("absorbance", field="absorbance")
_DLS = CalcMeasurement("dynamic light scattering", field="absorbance")

_LUNATIC_NODES: list[Node] = [
    _ABSORBANCE,
    _DLS,
    # a260
    CalcDoc(
        "Concentration",
        field="a260 concentration (ng/ul)",
        sources=["absorbance"],
        view="uuid",
        unit="ng/µL",
    ),
    CalcDoc(
        "Concentration",
        field="concentration (ng/ul)",
        sources=["absorbance"],
        view="uuid",
        unit="ng/µL",
    ),
    CalcDoc(
        "Background (A260)",
        field="background (a260)",
        sources=["absorbance"],
        view="uuid",
        unit="mAU",
    ),
    CalcDoc(
        "A260/A230",
        field="a260/a230",
        sources=["absorbance"],
        view="uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "A260/A280",
        field="a260/a280",
        sources=["absorbance"],
        view="uuid",
        unit=UNITLESS,
    ),
    # a280
    CalcDoc(
        "Concentration",
        field="concentration (mg/ml)",
        sources=["absorbance"],
        view="uuid",
        unit="mg/mL",
    ),
    CalcDoc(
        "Background (A280)",
        field="background (a280)",
        sources=["absorbance"],
        view="uuid",
        unit="mAU",
    ),
    CalcDoc(
        "A260/A280",
        field="a260/a280",
        sources=["absorbance"],
        view="uuid",
        unit=UNITLESS,
    ),
    # Dynamic Light Scattering
    CalcDoc(
        "KC/R (mol/g)",
        field="kc/r (mol/g)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "kD (ml/g)",
        field="kd (ml/g)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "B22",
        field="b22 (ml.mol/g^2)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Optical contrast constant K",
        field="optical contrast constant k (m^2 mol kg^-2)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Z Average Diameter",
        field="z ave. dia (nm)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="nm",
    ),
    CalcDoc(
        "Polydispersity Index",
        field="pdi",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Diameter Standard Deviation",
        field="sd dia (nm)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="nm",
    ),
    CalcDoc(
        "Diffusion coefficient",
        field="diffusion coefficient (um^2/s)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Peak of Interest Mean Diameter",
        field="peak of interest mean dia (nm)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="nm",
    ),
    CalcDoc(
        "Peak of Interest Mode Diameter",
        field="peak of interest mode dia (nm)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="nm",
    ),
    CalcDoc(
        "Peak of Interest Est. MW",
        field="peak of interest est. mw (kda)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="kDa",
    ),
    CalcDoc(
        "Peak of Interest Intensity",
        field="peak of interest intensity (%)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="%",
    ),
    CalcDoc(
        "Peak of Interest Mass",
        field="peak of interest mass (%)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="%",
    ),
    CalcDoc(
        "Peak of Interest Diffusion coefficient",
        field="peak of interest diffusion coefficient (um^2/s)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Peak of Interest Mass Mean Diameter",
        field="peak of interest mass mean dia (nm)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="nm",
    ),
    CalcDoc(
        "Peak of Interest Rayleigh Ratio R",
        field="peak of interest rayleigh ratio r (cm^-1)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Derived intensity (cps)",
        field="derived intensity (cps)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Rayleigh ratio R",
        field="rayleigh ratio r (cm^-1)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "kD goodness of fit",
        field="kd goodness of fit",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
        description_field="kd linear fit",
    ),
    CalcDoc(
        "B22 goodness of fit",
        field="b22 goodness of fit",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
        description_field="b22 linear fit",
    ),
    CalcDoc(
        "Viscosity at T (cP)",
        field="viscosity at t (cp)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Viscosity at 20°C (cP)",
        field="viscosity at 20°c (cp)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "RI at T",
        field="ri at t",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "RI at 20°C",
        field="ri at 20°c",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Diameter @ C=0",
        field="diameter @ c=0 (nm)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit="nm",
    ),
    CalcDoc(
        "Number of Peaks",
        field="number of peaks",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Number of Angles",
        field="number of angles",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Angles Measured",
        field="angles measured (°)",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
    CalcDoc(
        "Intercept",
        field="intercept",
        sources=["dynamic light scattering"],
        view="detection_uuid",
        unit=UNITLESS,
    ),
]


def create_calculated_data(
    measurement_groups: list[MeasurementGroup],
) -> list[CalculatedDocument]:
    elements = []
    for measurement_group in measurement_groups:
        elements += LunaticExtractor.get_elements(measurement_group.measurements)

    views = {
        "uuid": UuidView().apply(elements),
        "detection_uuid": FieldView("detection type", sub_view=UuidView()).apply(
            elements
        ),
    }
    return build_calc_docs(nodes=_LUNATIC_NODES, views=views)

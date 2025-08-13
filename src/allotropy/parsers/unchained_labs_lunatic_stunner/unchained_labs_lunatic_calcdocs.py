from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    MeasurementGroup,
)
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.unchained_labs_lunatic_stunner.extractor import LunaticExtractor
from allotropy.calcdocs.unchained_labs_lunatic_stunner.views import (
    DetectionTypeView,
    UuidView,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)


def create_calculated_data(
    measurement_groups: list[MeasurementGroup],
) -> list[CalculatedDocument]:
    elements = []
    for measurement_group in measurement_groups:
        elements += LunaticExtractor.get_elements(measurement_group.measurements)

    lunatic_view_data = UuidView().apply(elements)

    absorbance_conf = MeasurementConfig(
        name="absorbance",
        value="absorbance",
    )

    dynamic_light_scattering_conf = MeasurementConfig(
        name="dynamic light scattering",
        value="absorbance",
    )

    detection_type_view = DetectionTypeView(sub_view=UuidView()).apply(elements)

    configs = CalcDocsConfig(
        [
            # a260
            CalculatedDataConfig(
                name="Concentration",
                value="a260 concentration (ng/ul)",
                unit="ng/µL",
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            CalculatedDataConfig(
                name="Concentration",
                value="concentration (ng/ul)",
                unit="ng/µL",
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            CalculatedDataConfig(
                name="Background (A260)",
                value="background (a260)",
                unit="mAU",
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            CalculatedDataConfig(
                name="A260/A230",
                value="a260/a230",
                unit=UNITLESS,
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            CalculatedDataConfig(
                name="A260/A280",
                value="a260/a280",
                unit=UNITLESS,
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            # a280
            CalculatedDataConfig(
                name="Concentration",
                value="concentration (mg/ml)",
                unit="mg/mL",
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            CalculatedDataConfig(
                name="Background (A280)",
                value="background (a280)",
                unit="mAU",
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            CalculatedDataConfig(
                name="A260/A280",
                value="a260/a280",
                unit=UNITLESS,
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            CalculatedDataConfig(
                name="E1%",
                value="e1%",
                unit=UNITLESS,
                view_data=lunatic_view_data,
                source_configs=(absorbance_conf,),
            ),
            # Dynamic Light Scattering related calculations
            CalculatedDataConfig(
                name="KC/R (mol/g)",
                value="kc/r (mol/g)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="kD (ml/g)",
                value="kd (ml/g)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="B22",
                value="b22 (ml.mol/g^2)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Optical contrast constant K",
                value="optical contrast constant k (m^2 mol kg^-2)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Z Average Diameter",
                value="z ave. dia (nm)",
                unit="nm",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Polydispersity Index",
                value="pdi",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Diameter Standard Deviation",
                value="sd dia (nm)",
                unit="nm",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Diffusion coefficient",
                value="diffusion coefficient (um^2/s)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Peak of Interest Mean Diameter",
                value="peak of interest mean dia (nm)",
                unit="nm",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Peak of Interest Mode Diameter",
                value="peak of interest mode dia (nm)",
                unit="nm",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Peak of Interest Est. MW",
                value="peak of interest est. mw (kda)",
                unit="kDa",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Peak of Interest Intensity",
                value="peak of interest intensity (%)",
                unit="%",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Peak of Interest Mass",
                value="peak of interest mass (%)",
                unit="%",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Peak of Interest Diffusion coefficient",
                value="peak of interest diffusion coefficient (um^2/s)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Derived intensity (cps)",
                value="derived intensity (cps)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Rayleigh ratio R",
                value="rayleigh ratio r (cm^-1)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="kD goodness of fit",
                value="kd goodness of fit",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="B22 goodness of fit",
                value="b22 goodness of fit",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Viscosity at T (cP)",
                value="viscosity at t (cp)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Viscosity at 20°C (cP)",
                value="viscosity at 20°c (cp)",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="RI at T",
                value="ri at t",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="RI at 20°C",
                value="ri at 20°c",
                unit=UNITLESS,
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
            CalculatedDataConfig(
                name="Diameter @ C=0",
                value="diameter @ c=0 (nm)",
                unit="nm",
                view_data=detection_type_view,
                source_configs=(dynamic_light_scattering_conf,),
            ),
        ]
    )

    return [
        calc_doc
        for parent_calc_doc in configs.construct()
        for calc_doc in parent_calc_doc.iter_struct()
    ]

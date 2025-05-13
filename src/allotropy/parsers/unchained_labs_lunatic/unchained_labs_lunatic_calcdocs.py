from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    MeasurementGroup,
)
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.unchained_labs_lunatic.extractor import LunaticExtractor
from allotropy.calcdocs.unchained_labs_lunatic.views import UuidView
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
        ]
    )

    return [
        calc_doc
        for parent_calc_doc in configs.construct()
        for calc_doc in parent_calc_doc.iter_struct()
    ]

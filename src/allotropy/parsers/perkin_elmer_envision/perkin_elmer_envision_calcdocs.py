from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.perkin_elmer_envision.config import EnvisionCalculatedDataConfig
from allotropy.calcdocs.perkin_elmer_envision.views import PosView
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    PlateList,
    ReadType,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)


def create_calculated_data(
    plate_list: PlateList, read_type: ReadType
) -> list[CalculatedDocument]:
    pos_view = PosView()

    meas_config = MeasurementConfig(
        name=read_type.value,
        value="value",
    )

    configs = CalcDocsConfig(
        [
            EnvisionCalculatedDataConfig(
                name=calculated_plate.plate_info.name,
                description=calculated_plate.plate_info.formula,
                value="calc value",
                view_data=pos_view.special_apply(plate_list, calculated_plate),
                source_configs=(meas_config,),
                unit=UNITLESS,
                plate_number=calculated_plate.plate_info.number,
            )
            for calculated_plate in plate_list.calculated
        ]
    )

    return [
        calc_doc
        for parent_calc_doc in configs.construct()
        for calc_doc in parent_calc_doc.iter_struct()
    ]

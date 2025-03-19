from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.calcdocs.config import (
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    PlateList,
    ReadType,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)


def create_calculated_data(
    plate_list: PlateList, read_type: ReadType
) -> list[CalculatedDocument]:

    meas_config = MeasurementConfig(
        name=read_type.value,
        value="value",
    )

    for calculated_plate in plate_list.calculated:
        CalculatedDataConfig(
            name=calculated_plate.plate_info.name,
            description=calculated_plate.plate_info.formula,
            value="value",
            view_data=view_data,
            source_configs=(meas_config,),
        )

        for calculated_result, source_results in calculated_plate.get_result_and_sources(
            plate_list
        )

    return [
        CalculatedDocument(
            uuid=calculated_result.uuid,
            name=calculated_plate.plate_info.name,
            description=calculated_plate.plate_info.formula,
            value=calculated_result.value,
            unit=UNITLESS,
            data_sources=[
                DataSource(
                    reference=Referenceable(source_result.uuid),
                    feature=read_type.value,
                )
                for source_result in source_results
            ],
        )
        for calculated_plate in plate_list.calculated
        for calculated_result, source_results in calculated_plate.get_result_and_sources(
            plate_list
        )
    ]

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    CalculatedDataItem,
    DataSource,
)
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.perkin_elmer_envision.extractor import (
    PerkinElmerEnvisionExtractor,
)
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    PlateList,
    ReadType,
)


def create_calculated_data(
    plate_list: PlateList, read_type: ReadType
) -> list[CalculatedDataItem]:
    PerkinElmerEnvisionExtractor.get_elements_from_plate_list(plate_list)

    result_conf = MeasurementConfig(
        name="result",
        value="value",
    )

    calc_result = CalculatedDataConfig(
        # identifier=calculated_result.uuid,
        # name=calculated_plate.plate_info.name,
        # description=calculated_plate.plate_info.formula,
        # value=calculated_result.value,
        # unit=UNITLESS,
        name="sum mean",
        value="mean",
        view_data=mean_view_data,
        source_configs=(result_conf,),
    )

    configs = CalcDocsConfig(
        [
            calc_result,
        ]
    )

    [
        calc_doc
        for parent_calc_doc in configs.construct()
        for calc_doc in parent_calc_doc.iter_struct()
    ]

    return [
        CalculatedDataItem(
            identifier=calculated_result.uuid,
            name=calculated_plate.plate_info.name,
            description=calculated_plate.plate_info.formula,
            value=calculated_result.value,
            unit=UNITLESS,
            data_sources=[
                DataSource(
                    identifier=source_result.uuid,
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

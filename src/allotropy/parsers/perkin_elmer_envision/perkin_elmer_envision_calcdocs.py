from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    PlateList,
    ReadType,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def create_calculated_data(
    plate_list: PlateList, read_type: ReadType
) -> list[CalculatedDocument]:
    return [
        CalculatedDocument(
            uuid=random_uuid_str(),
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

from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
)
from allotropy.parser_factory import Vendor
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_parser import (
    PerkinElmerEnvisionParser,
)
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
)
from tests.parsers.perkin_elmer_envision.perkin_elmer_envision_data import (
    get_data,
    get_model,
)

VENDOR_TYPE = Vendor.PERKIN_ELMER_ENVISION


def test_get_model() -> None:
    data = get_data()
    mapper_data = Data(
        create_metadata(data.software, data.instrument, "file.txt"),
        create_measurement_groups(data),
        create_calculated_data(data.plate_list, data.labels.get_read_type()),
    )

    assert (
        PerkinElmerEnvisionParser()._get_mapper().map_model(mapper_data) == get_model()
    )

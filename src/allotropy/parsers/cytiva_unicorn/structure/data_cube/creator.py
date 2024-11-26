from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
)
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.parser import (
    DataCubeParser,
)


def get_data_cube_parser(
    handler: UnicornZipHandler,
    curve_element: StrictElement,
) -> DataCubeParser:
    names = ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
    data_name = curve_element.recursive_find(names).get_text()
    return DataCubeParser(handler.get_zip_from_pattern(data_name))


def create_data_cube(
    handler: UnicornZipHandler,
    curve_element: StrictElement,
    data_cuve_component: DataCubeComponent,
) -> DataCube:
    parser = get_data_cube_parser(handler, curve_element)
    return DataCube(
        label=curve_element.find("Name").get_text(),
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="retention time",
                unit="s",
            ),
        ],
        structure_measures=[data_cuve_component],
        dimensions=[parser.get_dimensions()],
        measures=[parser.get_measures()],
    )

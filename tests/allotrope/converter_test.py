from allotropy.allotrope.converter import structure, unstructure
from allotropy.allotrope.models.adm.cell_culture_analyzer.benchling._2023._09.cell_culture_analyzer import (
    AnalyteDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueMillimolePerLiter,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)


def test_data_cube() -> None:
    data_cube = TDatacube(
        cube_structure=TDatacubeStructure(
            dimensions=[
                TDatacubeComponent(
                    field_componentDatatype=FieldComponentDatatype("double"),
                    concept="elapsed time",
                    unit="s",
                ),
                TDatacubeComponent(
                    field_componentDatatype=FieldComponentDatatype("int"),
                    concept="wavelength",
                    unit=None,
                ),
            ],
            measures=[
                TDatacubeComponent(
                    field_componentDatatype=FieldComponentDatatype("double"),
                    concept="fluorescence",
                    unit="RFU",
                )
            ],
        ),
        data=TDatacubeData(
            dimensions=[[1.1, 2.2, 3.3], [1.0, 2.0, 3.0]],
            measures=[[4.0, 5.0, None]],
        ),
    )
    asm_dict = unstructure(data_cube)
    assert asm_dict == {
        "cube-structure": {
            "dimensions": [
                {
                    "@componentDatatype": "double",
                    "concept": "elapsed time",
                    "unit": "s",
                },
                {"@componentDatatype": "int", "concept": "wavelength"},
            ],
            "measures": [
                {
                    "@componentDatatype": "double",
                    "concept": "fluorescence",
                    "unit": "RFU",
                }
            ],
        },
        "data": {
            "dimensions": [[1.1, 2.2, 3.3], [1.0, 2.0, 3.0]],
            "measures": [[4.0, 5.0, None]],
        },
    }
    assert structure(asm_dict, TDatacube) == data_cube


def test_omits_null_values_except_for_specified_classes() -> None:
    item = AnalyteDocumentItem(
        analyte_name="test",
        molar_concentration=TNullableQuantityValueMillimolePerLiter(value=None),
    )
    asm_dict = unstructure(item)
    assert asm_dict == {
        "analyte name": "test",
        "molar concentration": {"unit": "mmol/L", "value": None},
    }
    assert structure(asm_dict, AnalyteDocumentItem) == item

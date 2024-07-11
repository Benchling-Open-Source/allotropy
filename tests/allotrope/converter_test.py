from dataclasses import field, make_dataclass

from allotropy.allotrope.converter import (
    add_custom_information_document,
    structure,
    unstructure,
)
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


def test_remove_none_fields_from_data_class_optional_none() -> None:
    test_data_class = make_dataclass(
        "test_data_class",
        [
            ("sample_id", str),
            ("volume", int),
            ("scientist", str | None, field(default=None)),  # type: ignore
        ],
    )
    test_class = test_data_class(sample_id="abc", volume=5, scientist=None)
    asm_dict = unstructure(test_class)
    assert asm_dict == {
        "sample id": "abc",
        "volume": 5,
    }
    assert structure(asm_dict, test_data_class) == test_class


def test_remove_none_fields_from_data_class_with_required_none() -> None:
    test_data_class = make_dataclass(
        "test_data_class",
        [("sample_id", str), ("volume", int), ("scientist", str | None)],  # type: ignore
    )
    test_class = test_data_class(sample_id="abc", volume=5, scientist=None)
    asm_dict = unstructure(test_class)
    assert asm_dict == {
        "sample id": "abc",
        "volume": 5,
        "scientist": None,
    }
    assert structure(asm_dict, test_data_class) == test_class


def test_custom_information_document() -> None:
    item = add_custom_information_document(
        AnalyteDocumentItem(
            analyte_name="test",
        ),
        {"extra key": "Value", "weird-key/(value)°": "Other value"},
    )

    assert item.custom_information_document.extra_key == "Value"  # type: ignore
    assert item.custom_information_document.weird_DASH_key_SLASH__OPAREN_value_CPAREN__DEG_ == "Other value"  # type: ignore
    asm_dict = unstructure(item)
    assert asm_dict == {
        "analyte name": "test",
        "custom information document": {
            "extra key": "Value",
            "weird-key/(value)°": "Other value",
        },
    }
    assert structure(asm_dict, AnalyteDocumentItem) == item

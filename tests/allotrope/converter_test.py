from dataclasses import dataclass, field, make_dataclass

from allotropy.allotrope.converter import (
    add_custom_information_document,
    structure,
    unstructure,
)
from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    DataProcessingDocument,
    ProcessedDataDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueUnitless,
    TQuantityValueUnitless,
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
    item = ProcessedDataDocumentItem(
        cycle_threshold_result=TNullableQuantityValueUnitless(value=None),
        data_processing_document=DataProcessingDocument(
            cycle_threshold_value_setting=TQuantityValueUnitless(value=1.0),
        ),
    )
    asm_dict = unstructure(item)
    assert asm_dict == {
        "cycle threshold result": {"value": None, "unit": "(unitless)"},
        "data processing document": {
            "cycle threshold value setting": {"value": 1.0, "unit": "(unitless)"},
        },
    }
    assert structure(asm_dict, ProcessedDataDocumentItem) == item


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
        ProcessedDataDocumentItem(
            cycle_threshold_result=TNullableQuantityValueUnitless(value=None),
            data_processing_document=DataProcessingDocument(
                cycle_threshold_value_setting=TQuantityValueUnitless(value=1.0),
            ),
        ),
        {"extra key": "Value", "$w.e\\ir:[d]-k'e~y/(v^a=l@ue)°#": "Other value"},
    )

    assert item.custom_information_document.extra_key == "Value"  # type: ignore
    assert item.custom_information_document._DOLLAR_w_POINT_e_BSLASH_ir_COLON__OBRACKET_d_CBRACKET__DASH_k_QUOTE_e_TILDE_y_SLASH__OPAREN_v_CARET_a_EQUALS_l_AT_ue_CPAREN__DEG__NUMBER_ == "Other value"  # type: ignore
    asm_dict = unstructure(item)
    assert asm_dict == {
        "cycle threshold result": {"value": None, "unit": "(unitless)"},
        "data processing document": {
            "cycle threshold value setting": {"value": 1.0, "unit": "(unitless)"},
        },
        "custom information document": {
            "extra key": "Value",
            "$w.e\\ir:[d]-k'e~y/(v^a=l@ue)°#": "Other value",
        },
    }
    assert structure(asm_dict, ProcessedDataDocumentItem) == item


def test_union_of_lists() -> None:
    @dataclass
    class D1:
        x: int

    @dataclass
    class D2:
        y: int

    @dataclass
    class HasUnionOfList:
        z: list[D1] | list[D2] | D2 | None = None

    obj = HasUnionOfList(z=[D1(1), D1(2)])
    obj_dict = unstructure(obj)
    assert obj_dict == {
        "z": [
            {
                "x": 1,
            },
            {
                "x": 2,
            },
        ]
    }
    assert structure(obj_dict, HasUnionOfList) == obj

    obj = HasUnionOfList(z=[D2(1)])
    obj_dict = unstructure(obj)
    assert obj_dict == {
        "z": [
            {
                "y": 1,
            },
        ]
    }
    assert structure(obj_dict, HasUnionOfList) == obj

    obj = HasUnionOfList(z=D2(1))
    obj_dict = unstructure(obj)
    assert obj_dict == {
        "z": {
            "y": 1,
        }
    }
    assert structure(obj_dict, HasUnionOfList) == obj

    obj = HasUnionOfList(z=None)
    obj_dict = unstructure(obj)
    assert obj_dict == {}
    assert structure(obj_dict, HasUnionOfList) == obj

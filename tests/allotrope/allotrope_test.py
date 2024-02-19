from allotropy.allotrope.allotrope import (
    serialize_allotrope,
    serialize_and_validate_allotrope,
)
from allotropy.allotrope.models.cell_culture_analyzer_benchling_2023_09_cell_culture_analyzer import (
    AnalyteDocumentItem,
)
from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    DeviceControlAggregateDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleDocument
from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueMillimolePerLiter,
    TQuantityValueNumber,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)


def test_serialize_and_validate_allotrope() -> None:
    model = Model()
    model.measurement_aggregate_document = MeasurementAggregateDocument(
        measurement_identifier="blah",
        plate_well_count=TQuantityValueNumber(1.0),
        measurement_document=[
            MeasurementDocumentItem(
                DeviceControlAggregateDocument(),
                SampleDocument(
                    well_location_identifier="well1", sample_identifier="sample1"
                ),
            )
        ],
    )
    assert serialize_and_validate_allotrope(model) == {
        "$asm.manifest": "http://purl.allotrope.org/manifests/fluorescence/BENCHLING/2023/09/fluorescence.manifest",
        "measurement aggregate document": {
            "measurement identifier": "blah",
            "plate well count": {
                "value": 1.0,
                "unit": "#",
            },
            "measurement document": [
                {
                    "device control aggregate document": {},
                    "sample document": {
                        "well location identifier": "well1",
                        "sample identifier": "sample1",
                    },
                }
            ],
        },
    }


def test_data_cube() -> None:
    data_cube = TDatacube(
        cube_structure=TDatacubeStructure(
            [
                TDatacubeComponent(
                    FieldComponentDatatype("double"), "elapsed time", "s"
                ),
                TDatacubeComponent(FieldComponentDatatype("int"), "wavelength", None),
            ],
            [
                TDatacubeComponent(
                    FieldComponentDatatype("double"), "fluorescence", "RFU"
                )
            ],
        ),
        data=TDatacubeData(
            [[1.1, 2.2, 3.3], [1.0, 2.0, 3.0]],
            [[4.0, 5.0, None]],
        ),
    )
    assert serialize_allotrope(data_cube) == {
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


def test_omits_null_values_except_for_specified_classes() -> None:
    item = AnalyteDocumentItem(
        "test", TNullableQuantityValueMillimolePerLiter(value=None)
    )

    assert serialize_allotrope(item) == {
        "analyte name": "test",
        "molar concentration": {"unit": "mmol/L", "value": None},
    }

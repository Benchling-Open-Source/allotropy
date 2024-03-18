from more_itertools import one
import pytest

from allotropy.allotrope.models.shared.components.plate_reader import (
    ProcessedDataDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueNumber,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.allotrope.models.ultraviolet_absorbance_benchling_2023_09_ultraviolet_absorbance import (
    ContainerType,
    DeviceControlDocumentItem,
    Model,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_model_from_file
from tests.parsers.test_utils import (
    from_file,
    validate_contents,
)

VENDOR_TYPE = Vendor.AGILENT_GEN5
SCHEMA_FILE = "ultraviolet-absorbance/BENCHLING/2023/09/ultraviolet-absorbance.json"

# This file was manually changed to use UTF-16 encoding to test encoding code paths. git history doesn't show this.
UTF_16_FILENAME = "endpoint_stdcurve_multiplate"

ABSORBENCE_FILENAMES = [
    "endpoint_pathlength_correct_singleplate",
    "endpoint_stdcurve_singleplate",
    "endpoint_stdcurve_singleplate_2",
    UTF_16_FILENAME,
    "kinetic_helper_gene_growth_curve",
    "kinetic_singleplate",
    "kinetic_multiplate",
]


@pytest.mark.parametrize("filename", ABSORBENCE_FILENAMES)
def test_to_allotrope_absorbance(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.txt"
    expected_filepath = (
        f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.json"
    )
    encoding = "UTF-16" if filename == UTF_16_FILENAME else None
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, encoding=encoding)
    validate_contents(allotrope_dict, expected_filepath)


def test_to_allotrope_absorbance_no_pm_in_time() -> None:
    test_filepath = "tests/parsers/agilent_gen5/testdata/absorbance/endpoint_pathlength_correct_singleplate_no_pm_in_time.txt"
    expected_filepath = "tests/parsers/agilent_gen5/testdata/absorbance/endpoint_pathlength_correct_singleplate.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


# Test allotrope_model_from_file().
def test_model_from_file_absorbance() -> None:
    filename = ABSORBENCE_FILENAMES[0]
    test_filepath = f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.txt"
    allotrope_model = allotrope_model_from_file(test_filepath, VENDOR_TYPE)
    assert isinstance(allotrope_model, Model)

    # Test many model fields fully. Don't test everything as that would mean a lot of hardcoding (or not-human-readable
    # pickle-ing, or something similar). Full end-to-end serialization is tested in test_to_allotrope_absorbance().
    measurement_aggregate_document = allotrope_model.measurement_aggregate_document
    assert measurement_aggregate_document
    assert measurement_aggregate_document.measurement_identifier  # randomly generated
    assert measurement_aggregate_document.plate_well_count == TQuantityValueNumber(96)
    assert (
        measurement_aggregate_document.measurement_time == "2023-09-15T12:30:00+00:00"
    )
    assert measurement_aggregate_document.analyst is None
    assert (
        measurement_aggregate_document.analytical_method_identifier
        == "C:\\Users\\user\\Desktop\\Plate123.prt"
    )
    assert (
        measurement_aggregate_document.experimental_data_identifier
        == "\\\\Mac\\Home\\Downloads\\ExperimentFile.xpt"
    )
    assert measurement_aggregate_document.experiment_type is None
    assert measurement_aggregate_document.container_type == ContainerType.well_plate
    assert measurement_aggregate_document.well_volume is None
    assert measurement_aggregate_document.device_system_document is None

    measurement_document_items = measurement_aggregate_document.measurement_document
    assert measurement_document_items
    assert len(measurement_document_items) == 96
    item = measurement_document_items[0]
    assert item

    device_control_aggregate_document = item.device_control_aggregate_document
    assert device_control_aggregate_document
    data_cube = item.data_cube
    assert data_cube
    assert item.compartment_temperature == TQuantityValueDegreeCelsius(26.3)
    processed_data_aggregate_document = item.processed_data_aggregate_document
    assert processed_data_aggregate_document
    assert item.mass_concentration is None

    control_docs = device_control_aggregate_document.device_control_document
    assert control_docs
    control_doc = one(control_docs)
    assert control_doc == DeviceControlDocumentItem()

    assert data_cube == TDatacube(
        label="endpoint data",
        cube_structure=TDatacubeStructure(
            dimensions=[
                TDatacubeComponent(
                    field_componentDatatype=FieldComponentDatatype.int,
                    concept="wavelength",
                    unit="nm",
                )
            ],
            measures=[
                TDatacubeComponent(
                    field_componentDatatype=FieldComponentDatatype.double,
                    concept="absorbance",
                    unit="mAU",
                )
            ],
        ),
        data=TDatacubeData(
            dimensions=[["977 [Test]", "900 [Ref]", "260", "280", "230"]],
            measures=[[0.056, 0.035, 0.626, 0.345, 0.331]],  # type: ignore[list-item]
        ),
    )

    processed_items = processed_data_aggregate_document.processed_data_document
    assert processed_items
    assert len(processed_items) == 10

    processed_item = processed_items[0]
    assert processed_item == ProcessedDataDocumentItem(
        processed_data=0.114, data_processing_description="260:Pathlength"
    )


@pytest.mark.parametrize(
    "filename",
    [
        "endpoint_singleplate",
        "endpoint_multiplate",
    ],
)
def test_to_allotrope_fluorescence(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/fluorescence/{filename}.txt"
    expected_filepath = (
        f"tests/parsers/agilent_gen5/testdata/fluorescence/{filename}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.parametrize(
    "filename",
    [
        "endpoint_singleplate",
        "endpoint_multiplate",
    ],
)
def test_to_allotrope_luminescence(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/luminescence/{filename}.txt"
    expected_filepath = (
        f"tests/parsers/agilent_gen5/testdata/luminescence/{filename}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match="No plate data found in file."):
        from_file("tests/parsers/agilent_gen5/testdata/garbage.txt", VENDOR_TYPE)

from allotropy.allotrope.allotrope import serialize_and_validate_allotrope
from allotropy.allotrope.models.adm.fluorescence.benchling._2023._09.fluorescence import (
    DeviceControlAggregateDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleDocument
from allotropy.allotrope.models.shared.definitions.custom import TQuantityValueNumber


def test_serialize_and_validate_allotrope() -> None:
    model = Model()
    model.measurement_aggregate_document = MeasurementAggregateDocument(
        measurement_identifier="blah",
        plate_well_count=TQuantityValueNumber(value=1.0),
        measurement_document=[
            MeasurementDocumentItem(
                device_control_aggregate_document=DeviceControlAggregateDocument(),
                sample_document=SampleDocument(
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

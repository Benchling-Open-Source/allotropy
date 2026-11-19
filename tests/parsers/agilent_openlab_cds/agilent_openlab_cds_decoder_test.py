from pathlib import Path

from allotropy.parsers.agilent_openlab_cds.agilent_openlab_cds_decoder import (
    decode_data,
)

TESTDATA = Path("tests/parsers/agilent_openlab_cds/testdata")


def test_decode_data_links_samples_to_their_own_injection() -> None:
    # The Luxo sequence runs a blank named "ACN" at two points, so the sample name alone does not
    # say which sample records belong to an injection.
    with open(TESTDATA / "Luxo HPLC-2023-09-01 07-52-44-04-00.rslt", "rb") as f:
        decoded = decode_data(f)

    injection_ids: dict[str, tuple[str, str]] = {}
    for result in decoded["Result Data"]:
        sample_data = result["Sample Data"]
        injection_ids[sample_data["RunDateTime"]] = (
            sample_data["SampleMeasurement"]["InjectionMeasData_ID"]["@id"],
            sample_data["SampleSetup"]["@id"],
        )

    assert injection_ids["2023-09-01T07:52:53.6410816-04:00"] == (
        "7a4a9a4f-cd42-4112-9849-34fb4a22feb0",
        "a13f3598-db40-442c-ada1-1120b053c362",
    )
    assert injection_ids["2023-09-01T08:24:44.0565147-04:00"] == (
        "842ab0e3-b504-4c89-b166-836ee49b27c0",
        "3b32bebf-f60b-4285-a6dd-841d91221cd5",
    )
    assert len(set(injection_ids.values())) == len(injection_ids)

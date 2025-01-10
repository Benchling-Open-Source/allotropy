from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    _get_plate_well_count,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    Header,
    Well,
    WellItem,
)


def test__get_plate_well_count_from_header() -> None:
    header = Header(
        measurement_time="",
        plate_well_count=96,
        experiment_type=ExperimentType.comparative_CT_qPCR_experiment,
        device_identifier="",
        model_number="",
        device_serial_number="",
        measurement_method_identifier="",
        pcr_detection_chemistry=None,
        passive_reference_dye_setting=None,
        barcode=None,
        analyst=None,
        experimental_data_identifier=None,
    )

    # If set in header, use that
    assert _get_plate_well_count(header, []) == 96


def test__get_plate_well_count_from_wells() -> None:
    header = Header(
        measurement_time="",
        plate_well_count=None,
        experiment_type=ExperimentType.comparative_CT_qPCR_experiment,
        device_identifier="",
        model_number="",
        device_serial_number="",
        measurement_method_identifier="",
        pcr_detection_chemistry=None,
        passive_reference_dye_setting=None,
        barcode=None,
        analyst=None,
        experimental_data_identifier=None,
    )

    # With max(identifier) == 1, max(position) == A1, well_plate_count == 1
    wells = [
        Well(
            identifier=1,
            items=[
                WellItem(
                    uuid="",
                    identifier=1,
                    target_dna_description="",
                    sample_identifier="",
                    position="A1",
                )
            ],
        )
    ]
    assert _get_plate_well_count(header, wells) == 1

    # With max(identifier) == 94, max(position) == A1, well_plate_count == 96
    wells = [
        Well(
            identifier=1,
            items=[
                WellItem(
                    uuid="",
                    identifier=1,
                    target_dna_description="",
                    sample_identifier="",
                    position="A1",
                ),
                WellItem(
                    uuid="",
                    identifier=94,
                    target_dna_description="",
                    sample_identifier="",
                    position=None,
                ),
            ],
        )
    ]
    assert _get_plate_well_count(header, wells) == 96

    # With max(identifier) == 1, max(position) == H13 (>H12), well_plate_count == 384
    wells = [
        Well(
            identifier=1,
            items=[
                WellItem(
                    uuid="",
                    identifier=1,
                    target_dna_description="",
                    sample_identifier="",
                    position=None,
                ),
                WellItem(
                    uuid="",
                    identifier=94,
                    target_dna_description="",
                    sample_identifier="",
                    position="H13",
                ),
            ],
        )
    ]
    assert _get_plate_well_count(header, wells) == 384

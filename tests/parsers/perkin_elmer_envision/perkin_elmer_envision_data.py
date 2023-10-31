from allotropy.allotrope.models.plate_reader_rec_2023_09_plate_reader import (
    ContainerType,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    SampleDocument,
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TRelativeFluorescenceUnit,
)
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    BasicAssayInfo,
    Data,
    Filter,
    Instrument,
    Labels,
    Plate,
    PlateInfo,
    PlateMap,
    Result,
)


def get_data() -> Data:
    return Data(
        plates=[
            Plate(
                plate_info=PlateInfo(
                    number="1",
                    barcode="Plate 1",
                    emission_filter_id="1st",
                    measurement_time="10/13/2022 3:08:06 PM",
                    measured_height=11.9,
                    chamber_temperature_at_start=23.17,
                ),
                results=[Result(col="A", row="01", value=31441)],
            ),
            Plate(
                plate_info=PlateInfo(
                    number="1",
                    barcode="Plate 1",
                    emission_filter_id="2nd",
                    measurement_time="10/13/2022 3:08:06 PM",
                    measured_height=11.9,
                    chamber_temperature_at_start=23.17,
                ),
                results=[Result(col="A", row="01", value=80368)],
            ),
        ],
        basic_assay_info=BasicAssayInfo("100302", "3134"),
        number_of_wells=96.0,
        plate_maps={
            "1": PlateMap(
                plate_n="1",
                group_n="1",
                sample_role_type_mapping={
                    "01": {"A": SampleRoleType.undefined_sample_role}
                },
            ),
        },
        labels=Labels(
            label="AC HTRF Laser [Eu]",
            excitation_filter=Filter("UV2 (TRF) 320", 320, 75),
            emission_filters={
                "1st": Filter("APC 665", 665, 75),
                "2nd": Filter("Cy5 620", 620, 10),
            },
            scan_position_setting=ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
            number_of_flashes=50,
            detector_gain_setting="2",
        ),
        instrument=Instrument(
            serial_number="1050209",
            nickname="EnVision",
        ),
    )


def get_model() -> Model:
    return Model(
        field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/REC/2023/09/plate-reader.manifest",
        plate_reader_aggregate_document=PlateReaderAggregateDocument(
            device_system_document=DeviceSystemDocument(
                model_number="1050209",
                device_identifier="EnVision",
            ),
            plate_reader_document=[
                PlateReaderDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_time="2022-10-13T15:08:06+00:00",
                        analytical_method_identifier="100302",
                        experimental_data_identifier="3134",
                        container_type=ContainerType.well_plate,
                        plate_well_count=TQuantityValueNumber(value=96.0),
                        measurement_document=[
                            FluorescencePointDetectionMeasurementDocumentItems(
                                measurement_identifier="",
                                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                                    device_control_document=[
                                        FluorescencePointDetectionDeviceControlDocumentItem(
                                            device_type="fluorescence detector",
                                            shaking_configuration_description=None,
                                            detector_distance_setting__plate_reader_=TQuantityValueMillimeter(
                                                value=11.9,
                                                has_statistic_datum_role=None,
                                                unit="mm",
                                                field_type=None,
                                            ),
                                            integration_time=None,
                                            number_of_averages=TQuantityValueNumber(
                                                value=50.0,
                                                has_statistic_datum_role=None,
                                                unit="#",
                                                field_type=None,
                                            ),
                                            detector_gain_setting="2",
                                            scan_position_setting__plate_reader_=ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
                                            detector_carriage_speed_setting=None,
                                            detector_wavelength_setting=TQuantityValueNanometer(
                                                value=665.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            detector_bandwidth_setting=TQuantityValueNanometer(
                                                value=75.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            excitation_bandwidth_setting=TQuantityValueNanometer(
                                                value=75.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            excitation_wavelength_setting=TQuantityValueNanometer(
                                                value=320.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            wavelength_filter_cutoff_setting=None,
                                            field_index=None,
                                        )
                                    ]
                                ),
                                sample_document=SampleDocument(
                                    location_identifier="A01",
                                    sample_identifier="Plate 1 A01",
                                    batch_identifier=None,
                                    sample_role_type=str(
                                        SampleRoleType.undefined_sample_role
                                    ),
                                    well_plate_identifier="Plate 1",
                                ),
                                compartment_temperature=TQuantityValueDegreeCelsius(
                                    value=23.17,
                                    has_statistic_datum_role=None,
                                    unit="degC",
                                    field_type=None,
                                ),
                                fluorescence=TRelativeFluorescenceUnit(31441),
                            )
                        ],
                    )
                ),
                PlateReaderDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_time="2022-10-13T15:08:06+00:00",
                        analytical_method_identifier="100302",
                        experimental_data_identifier="3134",
                        container_type=ContainerType.well_plate,
                        plate_well_count=TQuantityValueNumber(value=96.0),
                        measurement_document=[
                            FluorescencePointDetectionMeasurementDocumentItems(
                                measurement_identifier="",
                                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                                    device_control_document=[
                                        FluorescencePointDetectionDeviceControlDocumentItem(
                                            device_type="fluorescence detector",
                                            shaking_configuration_description=None,
                                            detector_distance_setting__plate_reader_=TQuantityValueMillimeter(
                                                value=11.9,
                                                has_statistic_datum_role=None,
                                                unit="mm",
                                                field_type=None,
                                            ),
                                            integration_time=None,
                                            number_of_averages=TQuantityValueNumber(
                                                value=50.0,
                                                has_statistic_datum_role=None,
                                                unit="#",
                                                field_type=None,
                                            ),
                                            detector_gain_setting="2",
                                            scan_position_setting__plate_reader_=ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
                                            detector_carriage_speed_setting=None,
                                            detector_wavelength_setting=TQuantityValueNanometer(
                                                value=620.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            detector_bandwidth_setting=TQuantityValueNanometer(
                                                value=10.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            excitation_bandwidth_setting=TQuantityValueNanometer(
                                                value=75.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            excitation_wavelength_setting=TQuantityValueNanometer(
                                                value=320.0,
                                                has_statistic_datum_role=None,
                                                unit="nm",
                                                field_type=None,
                                            ),
                                            wavelength_filter_cutoff_setting=None,
                                            field_index=None,
                                        )
                                    ]
                                ),
                                sample_document=SampleDocument(
                                    location_identifier="A01",
                                    sample_identifier="Plate 1 A01",
                                    batch_identifier=None,
                                    sample_role_type=str(
                                        SampleRoleType.undefined_sample_role
                                    ),
                                    well_plate_identifier="Plate 1",
                                ),
                                compartment_temperature=TQuantityValueDegreeCelsius(
                                    value=23.17,
                                    has_statistic_datum_role=None,
                                    unit="degC",
                                    field_type=None,
                                ),
                                fluorescence=TRelativeFluorescenceUnit(80368),
                            ),
                        ],
                    )
                ),
            ],
        ),
    )

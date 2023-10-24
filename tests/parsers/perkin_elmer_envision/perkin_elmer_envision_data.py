from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    ContainerType,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.components.plate_reader import (
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SampleRoleType,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValueNumber,
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
        manifest="http://purl.allotrope.org/manifests/fluorescence/BENCHLING/2023/09/fluorescence.manifest",
        measurement_aggregate_document=MeasurementAggregateDocument(
            measurement_identifier="",
            measurement_time="2022-10-13T15:08:06+00:00",
            analytical_method_identifier="100302",
            experimental_data_identifier="3134",
            container_type=ContainerType.well_plate,
            plate_well_count=TQuantityValueNumber(value=96.0),
            device_system_document=DeviceSystemDocument(
                model_number="1050209",
                device_identifier="EnVision",
            ),
            measurement_document=[
                MeasurementDocumentItem(
                    device_control_aggregate_document=DeviceControlAggregateDocument(
                        device_control_document=[
                            DeviceControlDocumentItem(
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
                        well_location_identifier="A01",
                        sample_identifier=None,
                        batch_identifier=None,
                        sample_role_type=SampleRoleType.undefined_sample_role,
                        plate_barcode="Plate 1",
                    ),
                    data_cube=None,
                    compartment_temperature=TQuantityValueDegreeCelsius(
                        value=23.17,
                        has_statistic_datum_role=None,
                        unit="degC",
                        field_type=None,
                    ),
                    processed_data_aggregate_document=ProcessedDataAggregateDocument(
                        processed_data_document=[
                            ProcessedDataDocumentItem(
                                processed_data=31441,
                                data_format_specification_type=None,
                                data_processing_description="processed data",
                            )
                        ]
                    ),
                    mass_concentration=None,
                ),
                MeasurementDocumentItem(
                    device_control_aggregate_document=DeviceControlAggregateDocument(
                        device_control_document=[
                            DeviceControlDocumentItem(
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
                        well_location_identifier="A01",
                        sample_identifier=None,
                        batch_identifier=None,
                        sample_role_type=SampleRoleType.undefined_sample_role,
                        plate_barcode="Plate 1",
                    ),
                    data_cube=None,
                    compartment_temperature=TQuantityValueDegreeCelsius(
                        value=23.17,
                        has_statistic_datum_role=None,
                        unit="degC",
                        field_type=None,
                    ),
                    processed_data_aggregate_document=ProcessedDataAggregateDocument(
                        processed_data_document=[
                            ProcessedDataDocumentItem(
                                processed_data=80368,
                                data_format_specification_type=None,
                                data_processing_description="processed data",
                            )
                        ]
                    ),
                    mass_concentration=None,
                ),
            ],
        ),
    )

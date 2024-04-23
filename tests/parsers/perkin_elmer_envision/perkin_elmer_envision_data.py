from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
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
    TQuantityValueRelativeFluorescenceUnit,
)
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_parser import (
    ReadType,
)
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    BackgroundInfo,
    BackgroundInfoList,
    BasicAssayInfo,
    CalculatedPlateInfo,
    CalculatedResult,
    CalculatedResultList,
    Data,
    Filter,
    Instrument,
    Labels,
    Plate,
    PlateList,
    PlateMap,
    Result,
    ResultList,
    ResultPlateInfo,
    Software,
)


def get_data() -> Data:
    return Data(
        plate_list=PlateList(
            plates=[
                Plate(
                    plate_info=ResultPlateInfo(
                        number="1",
                        barcode="Plate 1",
                        emission_filter_id="1st",
                        measinfo="1st Ex=Top Em=Top Wdw=1 (14)",
                        measurement_time="10/13/2022 3:08:06 PM",
                        measured_height=11.9,
                        chamber_temperature_at_start=23.17,
                        label="AC HTRF Laser [Eu]",
                    ),
                    background_info_list=BackgroundInfoList(
                        background_info=[
                            BackgroundInfo(
                                plate_num="1",
                                label="AC HTRF Laser [Eu]",
                                measinfo="De=1st Ex=Top Em=Top Wdw=1 (14)",
                            ),
                        ],
                    ),
                    calculated_result_list=CalculatedResultList([]),
                    result_list=ResultList(
                        [
                            Result(
                                uuid="80d11e7d-734c-4506-8087-335769da996c",
                                col="A",
                                row="01",
                                value=31441,
                            )
                        ]
                    ),
                ),
                Plate(
                    plate_info=ResultPlateInfo(
                        number="1",
                        barcode="Plate 1",
                        emission_filter_id="2nd",
                        measinfo="De=2nd Ex=Top Em=Top Wdw=1 (142)",
                        measurement_time="10/13/2022 3:08:06 PM",
                        measured_height=11.9,
                        chamber_temperature_at_start=23.17,
                        label="AC HTRF Laser [Eu]",
                    ),
                    background_info_list=BackgroundInfoList(
                        background_info=[
                            BackgroundInfo(
                                plate_num="1",
                                label="AC HTRF Laser [Eu]",
                                measinfo="De=2nd Ex=Top Em=Top Wdw=1 (142)",
                            ),
                        ],
                    ),
                    calculated_result_list=CalculatedResultList([]),
                    result_list=ResultList(
                        [
                            Result(
                                uuid="f2d4dd7c-0b02-4bd6-a6c5-8acd944e8d56",
                                col="A",
                                row="01",
                                value=80368,
                            )
                        ]
                    ),
                ),
                Plate(
                    plate_info=CalculatedPlateInfo(
                        number="1",
                        barcode="Plate 1",
                        measurement_time=None,
                        measured_height=None,
                        chamber_temperature_at_start=None,
                        formula="Calc 1: General = (X / Y) where X = AC HTRF Laser [Eu](1) Y = AC HTRF Laser [Eu](1)",
                        name="Calc 1: General",
                    ),
                    background_info_list=BackgroundInfoList(
                        background_info=[
                            BackgroundInfo(
                                plate_num="1",
                                label="AC HTRF Laser [Eu]",
                                measinfo="De=2nd Ex=Top Em=Top Wdw=1 (142)",
                            ),
                        ],
                    ),
                    calculated_result_list=CalculatedResultList(
                        calculated_results=[
                            CalculatedResult(
                                uuid="",
                                col="A",
                                row="01",
                                value=3,
                            )
                        ]
                    ),
                    result_list=ResultList([]),
                ),
            ],
        ),
        basic_assay_info=BasicAssayInfo("100302", "3134"),
        number_of_wells=96.0,
        plate_maps={
            "1": PlateMap(
                plate_n="1",
                group_n="1",
                sample_role_type_mapping={
                    "01": {"A": SampleRoleType.unknown_sample_role}
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
        software=Software(
            software_name="EnVision Workstation",
            software_version="1.0",
        ),
    )


def get_model() -> Model:
    return Model(
        field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        plate_reader_aggregate_document=PlateReaderAggregateDocument(
            device_system_document=DeviceSystemDocument(
                model_number="EnVision",
                equipment_serial_number="1050209",
                device_identifier="EnVision",
            ),
            data_system_document=DataSystemDocument(
                file_name="file.txt",
                software_name="EnVision Workstation",
                software_version="1.0",
                ASM_converter_name=ASM_CONVERTER_NAME,
                ASM_converter_version=ASM_CONVERTER_VERSION,
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
                                            ),
                                            integration_time=None,
                                            number_of_averages=TQuantityValueNumber(
                                                value=50.0,
                                            ),
                                            detector_gain_setting="2",
                                            scan_position_setting__plate_reader_=ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
                                            detector_carriage_speed_setting=None,
                                            detector_wavelength_setting=TQuantityValueNanometer(
                                                value=665.0,
                                            ),
                                            detector_bandwidth_setting=TQuantityValueNanometer(
                                                value=75.0,
                                            ),
                                            excitation_bandwidth_setting=TQuantityValueNanometer(
                                                value=75.0,
                                            ),
                                            excitation_wavelength_setting=TQuantityValueNanometer(
                                                value=320.0,
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
                                    sample_role_type=SampleRoleType.unknown_sample_role.value,
                                    well_plate_identifier="Plate 1",
                                ),
                                compartment_temperature=TQuantityValueDegreeCelsius(
                                    value=23.17,
                                ),
                                fluorescence=TQuantityValueRelativeFluorescenceUnit(
                                    31441
                                ),
                            ),
                            FluorescencePointDetectionMeasurementDocumentItems(
                                measurement_identifier="",
                                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                                    device_control_document=[
                                        FluorescencePointDetectionDeviceControlDocumentItem(
                                            device_type="fluorescence detector",
                                            shaking_configuration_description=None,
                                            detector_distance_setting__plate_reader_=TQuantityValueMillimeter(
                                                value=11.9,
                                            ),
                                            integration_time=None,
                                            number_of_averages=TQuantityValueNumber(
                                                value=50.0,
                                            ),
                                            detector_gain_setting="2",
                                            scan_position_setting__plate_reader_=ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
                                            detector_carriage_speed_setting=None,
                                            detector_wavelength_setting=TQuantityValueNanometer(
                                                value=620.0,
                                            ),
                                            detector_bandwidth_setting=TQuantityValueNanometer(
                                                value=10.0,
                                            ),
                                            excitation_bandwidth_setting=TQuantityValueNanometer(
                                                value=75.0,
                                            ),
                                            excitation_wavelength_setting=TQuantityValueNanometer(
                                                value=320.0,
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
                                    sample_role_type=SampleRoleType.unknown_sample_role.value,
                                    well_plate_identifier="Plate 1",
                                ),
                                compartment_temperature=TQuantityValueDegreeCelsius(
                                    value=23.17,
                                ),
                                fluorescence=TQuantityValueRelativeFluorescenceUnit(
                                    80368
                                ),
                            ),
                        ],
                    )
                ),
            ],
            calculated_data_aggregate_document=CalculatedDataAggregateDocument(
                calculated_data_document=[
                    CalculatedDataDocumentItem(
                        calculated_data_name="Calc 1: General",
                        calculation_description="Calc 1: General = (X / Y) where X = AC HTRF Laser [Eu](1) Y = AC HTRF Laser [Eu](1)",
                        calculated_data_identifier="",
                        calculated_result=TQuantityValue(
                            value=3,
                            unit=UNITLESS,
                        ),
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="f2d4dd7c-0b02-4bd6-a6c5-8acd944e8d56",
                                    data_source_feature=ReadType.FLUORESCENCE.value,
                                )
                            ]
                        ),
                    )
                ]
            ),
        ),
    )

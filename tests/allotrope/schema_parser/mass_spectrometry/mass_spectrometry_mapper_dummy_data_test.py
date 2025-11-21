from allotropy.allotrope.allotrope import serialize_and_validate_allotrope
from allotropy.allotrope.schema_mappers.adm.mass_spectrometry.rec._2025._06.mass_spectrometry import (
    Data,
    DetectorControl,
    Device,
    Mapper,
    Measurement,
    Metadata,
    Peak,
    SampleIntroduction,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser


def build_dummy_data() -> Data:
    return Data(
        metadata=Metadata(
            asset_management_identifier="asset-management-identifier-001",
            data_processing_description="example data processing description",
            devices=[
                Device(
                    device_type="spectrometer",
                    model_number="example model number",
                    product_manufacturer="example product manufacturer",
                    device_custom_info={
                        "example device custom info key": "example device custom info value"
                    },
                ),
                Device(
                    device_type="spectrometer",
                    model_number="example model number",
                    product_manufacturer="example product manufacturer",
                    device_custom_info={
                        "example device custom info key": "example device custom info value"
                    },
                ),
            ],
            device_system_custom_info={
                "example device system custom info key": "example device system custom info value"
            },
        ),
        measurements=[
            Measurement(
                analyst="example analyst",
                submitter="example submitter",
                measurement_mode_setting="example measurement mode setting",
                sample_identifier="sample-identifier-001",
                detector_control=DetectorControl(
                    detection_type="example detection type",
                    detection_duration_setting=1.0,
                    detector_relative_offset_setting=1.0,
                    detector_sampling_rate_setting=1.0,
                    m_z_maximum_setting=1.0,
                    m_z_minimum_setting=1.0,
                    polarity_setting="example polarity setting",
                ),
                sample_introduction=SampleIntroduction(
                    sample_introduction_medium="example sample introduction medium",
                    sample_introduction_mode_setting="example sample introduction mode setting",
                    flow_rate_setting=1.0,
                    laser_firing_frequency_setting=1.0,
                    sample_introduction_description="example sample introduction description",
                ),
                processed_data_types=[
                    "example processed data types",
                    "example processed data types",
                ],
                data_processing_types=[
                    "example data processing types",
                    "example data processing types",
                ],
            ),
            Measurement(
                analyst="example analyst",
                submitter="example submitter",
                measurement_mode_setting="example measurement mode setting",
                sample_identifier="sample-identifier-002",
                detector_control=DetectorControl(
                    detection_type="example detection type",
                    detection_duration_setting=1.0,
                    detector_relative_offset_setting=1.0,
                    detector_sampling_rate_setting=1.0,
                    m_z_maximum_setting=1.0,
                    m_z_minimum_setting=1.0,
                    polarity_setting="example polarity setting",
                ),
                sample_introduction=SampleIntroduction(
                    sample_introduction_medium="example sample introduction medium",
                    sample_introduction_mode_setting="example sample introduction mode setting",
                    flow_rate_setting=1.0,
                    laser_firing_frequency_setting=1.0,
                    sample_introduction_description="example sample introduction description",
                ),
                processed_data_types=[
                    "example processed data types",
                    "example processed data types",
                ],
                data_processing_types=[
                    "example data processing types",
                    "example data processing types",
                ],
            ),
        ],
        peaks=[
            Peak(
                identifier="identifier-001",
                m_z=1.0,
                mass=1.0,
                peak_area_value=1.0,
                peak_area_unit="example peak area unit",
                peak_height_value=1.0,
                peak_height_unit="example peak height unit",
                peak_width_value=1.0,
                peak_width_unit="example peak width unit",
                relative_peak_area=1.0,
                relative_peak_height=1.0,
                written_name="example written name",
            ),
            Peak(
                identifier="identifier-002",
                m_z=1.0,
                mass=1.0,
                peak_area_value=1.0,
                peak_area_unit="example peak area unit",
                peak_height_value=1.0,
                peak_height_unit="example peak height unit",
                peak_width_value=1.0,
                peak_width_unit="example peak width unit",
                relative_peak_area=1.0,
                relative_peak_height=1.0,
                written_name="example written name",
            ),
        ],
    )


def test_mass_spectrometry_mapper_dummy_data() -> None:
    # It just validates that the mapper and serializer can handle the dummy data without raising an exception
    data = build_dummy_data()
    mapper_output = Mapper(
        "asm_converter_name", lambda time: TimestampParser().parse(time)
    ).map_model(data)
    serialize_and_validate_allotrope(mapper_output)

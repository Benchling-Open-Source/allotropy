from allotropy.allotrope.models.adm.plate_reader.rec._2025._03.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_reader import AgilentGen5Reader
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    create_kinetic_results,
    create_metadata,
    create_results,
    create_spectrum_results,
    get_identifiers,
    get_kinetic_measurements,
    get_results_section,
    get_temperature,
    HeaderData,
    KineticData,
    ReadData,
)
from allotropy.parsers.agilent_gen5.constants import (
    NO_MEASUREMENTS_ERROR,
    ReadType,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5Parser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent Gen5"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AgilentGen5Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AgilentGen5Reader(named_file_contents)

        if (results_section := get_results_section(reader)) is None:
            reader.header_data.get_unread()
            raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

        header_data = HeaderData.create(
            reader.header_data, named_file_contents.original_file_path
        )
        read_data = ReadData.create(reader.sections["Procedure Details"])
        kinetic_data = KineticData.create(reader.sections["Procedure Details"])

        sample_identifiers = get_identifiers(reader.sections.get("Layout"))
        actual_temperature = get_temperature(reader.sections.get("Actual Temperature"))
        kinetic_result = get_kinetic_measurements(reader.sections.get("Time"))
        kinetic_measurements, kinetic_elapsed_time, kinetic_errors = kinetic_result or (
            {},
            [],
            {},
        )

        if kinetic_data and not (kinetic_measurements and kinetic_elapsed_time):
            msg = "Kinetic data is present in the file but no kinetic measurements data is found."
            raise AllotropeConversionError(msg)

        read_is_spectral = read_data[0].read_type == ReadType.SPECTRUM
        if read_is_spectral and reader.sections.get("Wavelength"):
            (
                wavelength_measurements,
                wavelength_calculated_data,
            ) = create_spectrum_results(
                header_data,
                read_data_list=read_data,
                wavelengths_sections=reader.sections.get("Wavelength"),
                sample_identifiers=sample_identifiers,
                actual_temperature=actual_temperature,
                results_section=results_section,
            )

            if not wavelength_measurements:
                raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

            return Data(
                metadata=create_metadata(header_data),
                measurement_groups=wavelength_measurements,
                calculated_data=wavelength_calculated_data,
            )

        if kinetic_data:
            measurement_groups, calculated_data = create_kinetic_results(
                results_section,
                header_data,
                read_data,
                sample_identifiers,
                actual_temperature,
                kinetic_data,
                kinetic_measurements,
                kinetic_elapsed_time,
                kinetic_errors,
            )
        else:
            measurement_groups, calculated_data = create_results(
                results_section,
                header_data,
                read_data,
                sample_identifiers,
                actual_temperature,
            )

        if not measurement_groups:
            raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

        return Data(
            metadata=create_metadata(header_data),
            measurement_groups=measurement_groups,
            calculated_data=calculated_data,
        )

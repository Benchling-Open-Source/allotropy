from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
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
    get_identifiers,
    get_kinetic_measurements,
    get_temperature,
    HeaderData,
    KineticData,
    ReadData,
)
from allotropy.parsers.agilent_gen5.constants import (
    DEFAULT_EXPORT_FORMAT_ERROR,
    NO_MEASUREMENTS_ERROR,
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

        if "Results" not in reader.sections:
            raise AllotropeConversionError(DEFAULT_EXPORT_FORMAT_ERROR)

        header_data = HeaderData.create(
            reader.header_data, named_file_contents.original_file_name
        )
        read_data = ReadData.create(reader.sections["Procedure Details"])
        kinetic_data = KineticData.create(reader.sections["Procedure Details"])

        sample_identifiers = get_identifiers(reader.sections.get("Layout"))
        actual_temperature = get_temperature(reader.sections.get("Actual Temperature"))
        kinetic_measurements, kinetic_elapsed_time = get_kinetic_measurements(
            reader.sections.get("Time")
        ) or ({}, [])

        if kinetic_data and not (kinetic_measurements and kinetic_elapsed_time):
            msg = "Kinetic data is present in the file but no kinetic measurements data is found."
            raise AllotropeConversionError(msg)

        # in case of single kinetic section, each well will contain one measurement document with the kinetic data cube
        # otherwise each well will contain multiple measurement documents
        if kinetic_data:
            measurement_groups, calculated_data = create_kinetic_results(
                reader.sections["Results"],
                header_data,
                read_data,
                sample_identifiers,
                actual_temperature,
                kinetic_data,
                kinetic_measurements,
                kinetic_elapsed_time,
            )
        else:
            measurement_groups, calculated_data = create_results(
                reader.sections["Results"],
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

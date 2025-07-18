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
    create_metadata,
    Gen5DataContext,
    get_concentrations,
    get_identifiers,
    get_kinetic_measurements,
    get_results_section,
    get_temperature,
    HeaderData,
    KineticData,
    KineticResultProcessor,
    ReadData,
    ResultProcessor,
    SpectralResultProcessor,
    StandardResultProcessor,
)
from allotropy.parsers.agilent_gen5.constants import (
    NO_MEASUREMENTS_ERROR,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5Parser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent Gen5"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AgilentGen5Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def __init__(self, timestamp_parser: TimestampParser | None = None):
        super().__init__(timestamp_parser)
        self._processors = [
            SpectralResultProcessor(),
            KineticResultProcessor(),
            StandardResultProcessor(),
        ]

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AgilentGen5Reader(named_file_contents)
        context = self._extract_data_context(
            reader, named_file_contents.original_file_path
        )

        processor = self._get_processor(context)
        measurement_groups, calculated_data = processor.process(context)

        if not measurement_groups:
            raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

        return Data(
            metadata=create_metadata(context.header_data),
            measurement_groups=measurement_groups,
            calculated_data=calculated_data,
        )

    def _extract_data_context(
        self, reader: AgilentGen5Reader, file_path: str
    ) -> Gen5DataContext:
        results_section = get_results_section(reader)
        if not results_section:
            reader.header_data.get_unread()
            raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

        kinetic_result = get_kinetic_measurements(reader.time_section)
        kinetic_measurements, kinetic_elapsed_time, kinetic_errors = kinetic_result or (
            {},
            [],
            {},
        )

        return Gen5DataContext(
            header_data=HeaderData.create(reader.header_data, file_path),
            read_data=ReadData.create(reader.procedure_details),
            kinetic_data=KineticData.create(reader.procedure_details),
            results_section=results_section,
            sample_identifiers=get_identifiers(reader.layout_section),
            concentration_values=get_concentrations(reader.layout_section),
            actual_temperature=get_temperature(reader.actual_temperature_section),
            kinetic_measurements=kinetic_measurements,
            kinetic_elapsed_time=kinetic_elapsed_time,
            kinetic_errors=kinetic_errors,
            wavelength_section=reader.wavelength_section,
        )

    def _get_processor(self, context: Gen5DataContext) -> ResultProcessor:
        """Get the appropriate processor for the given context."""
        for processor in self._processors:
            if processor.can_process(context):
                return processor

        msg = "No suitable processor found for the data."
        raise AllotropeConversionError(msg)

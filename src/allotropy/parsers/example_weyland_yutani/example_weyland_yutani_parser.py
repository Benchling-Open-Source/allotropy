from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.example_weyland_yutani.example_weyland_yutani_reader import (
    ExampleWeylandYutaniReader,
)
from allotropy.parsers.example_weyland_yutani.example_weyland_yutani_structure import (
    BasicAssayInfo,
    create_measurement_group,
    create_metadata,
    Instrument,
    Plate,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class ExampleWeylandYutaniParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Example Weyland Yutani"
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = ExampleWeylandYutaniReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = ExampleWeylandYutaniReader(named_file_contents)
        basic_assay_info = BasicAssayInfo.create(reader.bottom)
        instrument = Instrument.create()
        plates = Plate.create(reader.middle)

        if plates[0].number_of_wells is None:
            msg = "Unable to determine the number of wells in the plate."
            raise AllotropeConversionError(msg)

        return Data(
            create_metadata(instrument, named_file_contents.original_file_path),
            [create_measurement_group(plate, basic_assay_info) for plate in plates],
        )

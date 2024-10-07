from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_data_creator import (
    create_calculated_data,
    create_data,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppBioQuantStudioDesignandanalysisParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "AppBio QuantStudio Design & Analysis"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = DesignQuantstudioReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        data = create_data(DesignQuantstudioReader.create(named_file_contents))
        return Data(
            create_metadata(
                data.header,
                named_file_contents.original_file_name,
                data.experiment_type,
            ),
            create_measurement_groups(data.wells.wells, data.header),
            create_calculated_data(data),
        )

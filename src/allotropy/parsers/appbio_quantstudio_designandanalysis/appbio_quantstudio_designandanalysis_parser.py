from allotropy.allotrope.models.adm.pcr.rec._2024._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_parser import (
    AppBioQuantStudioParser,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_reader import (
    AppBioQuantStudioXLSXReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis import constants
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

    def parse_rt_pcr(
        self, reader: DesignQuantstudioReader, original_file_path: str
    ) -> Data:
        rt_pcr_reader = AppBioQuantStudioXLSXReader(reader.contents, reader.header)
        data = AppBioQuantStudioParser().parse_data(rt_pcr_reader, original_file_path)

        data.metadata.data_system_instance_identifier = "N/A"
        data.metadata.device_type = constants.DEVICE_TYPE
        data.metadata.container_type = constants.CONTAINER_TYPE
        data.metadata.product_manufacturer = constants.PRODUCT_MANUFACTURER
        data.metadata.software_name = constants.RT_PCR_SOFTWARE_NAME
        data.metadata.software_version = constants.RT_PCR_SOFTWARE_VERSION

        return data

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = DesignQuantstudioReader.create(named_file_contents)

        # special case to be handle by RT-Pcr quantstudio adapter
        if reader.has_sheet("Sample Setup"):
            return self.parse_rt_pcr(reader, named_file_contents.original_file_path)

        data = create_data(reader)
        return Data(
            create_metadata(
                data.header,
                named_file_contents.original_file_path,
                data.experiment_type,
            ),
            create_measurement_groups(data),
            create_calculated_data(data),
        )

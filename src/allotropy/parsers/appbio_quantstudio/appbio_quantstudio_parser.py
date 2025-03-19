from allotropy.allotrope.models.adm.pcr.rec._2024._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import Data, Mapper
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_calculated_documents import (
    iter_calculated_data_documents,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_reader import (
    AppBioQuantStudioReader,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    create_amplification_data,
    create_multicomponent_data,
    Header,
    MeltCurveRawData,
    Result,
    Well,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppBioQuantStudioParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "AppBio QuantStudio RT-PCR"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AppBioQuantStudioReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def parse_data(
        self, reader: AppBioQuantStudioReader, original_file_path: str
    ) -> Data:
        # Data sections must be read in order from the file.
        header = Header.create(reader.header)
        wells = Well.create(reader, header.experiment_type)
        amp_data = create_amplification_data(reader)
        multi_data = create_multicomponent_data(reader)
        results_data, result_metadata = Result.create(reader, header.experiment_type)
        melt_data = MeltCurveRawData.create(reader)

        calculated_data_documents = iter_calculated_data_documents(
            [well_item for well in wells for well_item in well.items],
            header.experiment_type,
            result_metadata.reference_sample_description,
            result_metadata.reference_dna_description,
        )

        return Data(
            metadata=create_metadata(header, original_file_path),
            measurement_groups=create_measurement_groups(
                header,
                wells,
                amp_data,
                multi_data,
                results_data,
                melt_data,
                result_metadata,
            ),
            calculated_data=create_calculated_data(calculated_data_documents),
        )

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AppBioQuantStudioReader.create(named_file_contents)
        return self.parse_data(reader, named_file_contents.original_file_path)

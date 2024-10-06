from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_calculated_documents import (
    iter_calculated_data_documents,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    create_amplification_data,
    create_multicomponent_data,
    Header,
    MeltCurveRawData,
    RawData,
    Result,
    Well,
)
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppBioQuantStudioParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "AppBio QuantStudio RT-PCR"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = LinesReader.create(named_file_contents)

        # Data sections must be read in order from the file.
        header = Header.create(reader)
        wells = Well.create(reader, header.experiment_type)
        # Skip raw data section
        RawData.create(reader)
        amp_data = create_amplification_data(reader)
        multi_data = create_multicomponent_data(reader)
        results_data, results_metadata = Result.create(reader, header.experiment_type)
        melt_data = MeltCurveRawData.create(reader)

        calculated_data_documents = iter_calculated_data_documents(
            [well_item for well in wells for well_item in well.items],
            header.experiment_type,
            results_metadata.reference_sample_description,
            results_metadata.reference_dna_description,
        )

        return Data(
            metadata=create_metadata(header, named_file_contents.original_file_name),
            measurement_groups=create_measurement_groups(
                header, wells, amp_data, multi_data, results_data, melt_data
            ),
            calculated_data=create_calculated_data(
                calculated_data_documents, results_metadata
            ),
        )

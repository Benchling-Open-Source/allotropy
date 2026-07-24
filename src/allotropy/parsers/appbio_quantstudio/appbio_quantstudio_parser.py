import openpyxl

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
    enrich_wells_with_results,
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
    SUPPORTED_DETECTION_MODES = "Fluorescence"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            if named_file_contents.extension == "txt":
                named_file_contents.contents.seek(0)
                raw = named_file_contents.contents.read(8192)
                text = (
                    raw.decode("utf-8", errors="replace")
                    if isinstance(raw, bytes)
                    else raw
                )
                lines = text.splitlines()
                has_star_keys = any(
                    line.startswith("* ") and " = " in line for line in lines[:10]
                )
                has_brackets = any(line.startswith("[") for line in lines)
                return has_star_keys or has_brackets
            # xlsx: QuantStudio XLSX files have sheet names wrapped in brackets
            wb = openpyxl.load_workbook(
                named_file_contents.get_bytes_stream(), read_only=True
            )
            sheet_names = wb.sheetnames
            wb.close()
            return any(name.startswith("[") for name in sheet_names)
        except Exception:
            return False

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

        # Create immutable copies of wells with results attached
        enriched_wells = enrich_wells_with_results(wells, results_data)

        calculated_data_documents = iter_calculated_data_documents(
            [well_item for well in enriched_wells for well_item in well.items],
            header.experiment_type,
            result_metadata.reference_sample_description,
            result_metadata.reference_dna_description,
        )

        return Data(
            metadata=create_metadata(header, original_file_path),
            measurement_groups=create_measurement_groups(
                header,
                enriched_wells,
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

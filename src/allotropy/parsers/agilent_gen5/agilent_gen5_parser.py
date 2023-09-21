import io
import itertools
from typing import Any

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.agilent_gen5.create_plate_data import create_plate_data
from allotropy.parsers.agilent_gen5.plate_data import PlateData
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5Parser(VendorParser):
    def _get_plate_chunks(self, contents: str) -> list[str]:
        return contents.strip().replace("\r\n", "\n").split(4 * "\n")

    def _parse(self, contents: io.IOBase, filename: str) -> Any:  # noqa: ARG002
        plates: list[PlateData] = []
        software_version_chunk = None
        file_paths_chunk = None
        all_data_chunk = None

        plate_chunks = self._get_plate_chunks(self._read_contents(contents))
        completed_plate = False
        for plate_chunk in plate_chunks:
            if plate_chunk.startswith("Software Version"):
                if completed_plate:
                    new_plate = create_plate_data(
                        software_version_chunk, file_paths_chunk, all_data_chunk
                    )
                    plates.append(new_plate)
                    completed_plate = False
                software_version_chunk = plate_chunk
            elif plate_chunk.startswith("Experiment File Path"):
                file_paths_chunk = plate_chunk
            elif plate_chunk.startswith("Plate Number"):
                all_data_chunk = plate_chunk
                completed_plate = True
            elif plate_chunk.startswith("Actual Temperature"):
                all_data_chunk = f"{all_data_chunk}\n\n{plate_chunk}"

        if completed_plate:
            new_plate = create_plate_data(
                software_version_chunk, file_paths_chunk, all_data_chunk
            )
            plates.append(new_plate)

        if not plates:
            msg = "No plate data found in file"
            raise AllotropeConversionError(msg)

        first_plate = plates[0]
        # TODO we just use the metadata for the first plate, but in theory they could all have
        # different metadata in particular, timestamp is known to be, but not sure on procedures/
        # plate dimensions/etc., need to follow up
        measurement_docs = list(
            itertools.chain.from_iterable([plate.measurement_docs for plate in plates])
        )
        model = first_plate.to_allotrope(measurement_docs)
        model.measurement_aggregate_document.measurement_time = self.get_date_time(
            model.measurement_aggregate_document.measurement_time
        )
        return model

        # TODO stats docs
        # statistics_docs = [plate.statistics_doc for plate in plates]
        # all_statistics_docs = list(itertools.chain.from_iterable(statistics_docs))
        # if all_statistics_docs:
        #     allotrope_dict["measurement aggregate document"]["statistics aggregate document"] = {
        #         "statistics document": all_statistics_docs,
        #     }

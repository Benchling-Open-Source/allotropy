import io
import itertools
from typing import Any

from allotropy.parsers.agilent_gen5.agilent_gen5_structure import Data
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5Parser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Any:  # noqa: ARG002
        section_lines_reader = SectionLinesReader(contents, encoding=None)
        data = Data.create(section_lines_reader)

        first_plate = data.plates[0]
        # TODO we just use the metadata for the first plate, but in theory they could all have
        # different metadata in particular, timestamp is known to be, but not sure on procedures/
        # plate dimensions/etc., need to follow up
        measurement_docs = list(
            itertools.chain.from_iterable(
                [plate.measurement_docs for plate in data.plates]
            )
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

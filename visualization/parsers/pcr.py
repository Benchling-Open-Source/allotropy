from typing import Any

from parsers.parser import Parser


class QpcrParser(Parser):
    MANIFEST = "http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest"

    def get_measurement_docs(self) -> dict[str, Any]:
        return {
            measurement_doc["measurement identifier"]: measurement_doc
            for qpcr_doc in self.asm_dict["qPCR aggregate document"]["qPCR document"]
            for measurement_doc in qpcr_doc["measurement aggregate document"][
                "measurement document"
            ]
        }

    def get_calc_docs(self) -> dict[str, Any]:
        qpcr_doc = self.asm_dict["qPCR aggregate document"]
        calculated_agg_document = qpcr_doc["calculated data aggregate document"]
        return {
            calc_doc["calculated data identifier"]: calc_doc
            for calc_doc in calculated_agg_document["calculated data document"]
        }

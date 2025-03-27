from typing import ClassVar

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_standard_curve_calc_docs,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.constants import (
    ExperimentType,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.creator import (
    Creator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
    Header,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.standard_curve.structure import (
    StandardCurveWellList,
)


class StandardCurveCreator(Creator):
    PLUGIN_REGEX: ClassVar[str] = r"Standard Curve"
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "Standard Curve Result",
    ]

    @classmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        header = Header.create(reader.header)
        wells = StandardCurveWellList.create(reader, header)
        well_items = wells.get_well_items()

        return Data(
            header,
            wells,
            experiment_type=ExperimentType.standard_curve_qpcr_experiment,
            calculated_documents=list(
                iter_standard_curve_calc_docs(well_items=well_items)
            ),
            reference_target=None,
            reference_sample=None,
        )

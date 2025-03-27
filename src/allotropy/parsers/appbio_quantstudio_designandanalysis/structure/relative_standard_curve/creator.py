from typing import ClassVar

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_relative_standard_curve_calc_docs,
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
    Result,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.relative_standard_curve.structure import (
    RelativeStandardCurveWellList,
)


class RelativeStandardCurveCreator(Creator):
    PLUGIN_REGEX: ClassVar[str] = r"Relative Quantification"
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "RQ Replicate Group Result",
    ]

    @classmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        header = Header.create(reader.header)
        wells = RelativeStandardCurveWellList.create(reader, header)
        well_items = wells.get_well_items()

        r_sample = Result.get_reference_sample(reader)
        r_target = Result.get_reference_target(reader)

        return Data(
            header,
            wells,
            experiment_type=ExperimentType.relative_standard_curve_qpcr_experiment,
            calculated_documents=list(
                iter_relative_standard_curve_calc_docs(
                    well_items=well_items,
                    r_sample=r_sample,
                    r_target=r_target,
                )
            ),
            reference_target=r_target,
            reference_sample=r_sample,
        )

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


def _has_valid_rq_values(reader: DesignQuantstudioReader) -> bool:
    """Return True if the RQ Replicate Group Result sheet contains at least one
    non-null Rq value.

    When all Rq values are null or nan (e.g. the reference calibrator sample
    was not processed or all wells undetermined), the reference sample cannot be
    inferred and RQ-derived calculated data documents must be skipped.
    """
    sheet = reader.get_non_empty_sheet_or_none("RQ Replicate Group Result")
    if sheet is None or "Rq" not in sheet.columns:
        return False
    return bool(sheet["Rq"].notna().any())


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

        if not _has_valid_rq_values(reader):
            r_sample = None
            r_target = None
        else:
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

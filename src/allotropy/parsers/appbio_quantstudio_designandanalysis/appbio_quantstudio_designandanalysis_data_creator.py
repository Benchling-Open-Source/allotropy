from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.genotyping.creator import (
    GenotypingCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.melt_curve.creator import (
    MeltCurveCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.presence_absence.creator import (
    PresenceAbsenceCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.primary_analysis.creator import (
    PrimaryAnalysisCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.relative_standard_curve.creator import (
    RelativeStandardCurveCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.standard_curve.creator import (
    StandardCurveCreator,
)


def create_data(contents: DesignQuantstudioContents) -> Data:
    possible_creators = [
        creator
        for creator in [
            StandardCurveCreator,
            RelativeStandardCurveCreator,
            GenotypingCreator,
            MeltCurveCreator,
            PresenceAbsenceCreator,
            PrimaryAnalysisCreator,
        ]
        if creator.check_type(contents)
    ]

    if len(possible_creators) == 1:
        return possible_creators[0].create(contents)

    msg = "Unable to infer experiment type from sheets in the input"
    raise AllotropeConversionError(msg)

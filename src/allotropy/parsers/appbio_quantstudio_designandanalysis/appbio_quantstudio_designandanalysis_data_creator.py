from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Data,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.creators import (
    genotyping,
    melt_curve,
    presence_absence,
    relative_standard_curve,
    standard_curve,
)


def create_data(contents: DesignQuantstudioContents) -> Data:
    possible_creators = [
        creator
        for creator in [
            standard_curve.StandardCurveCreator,
            relative_standard_curve.RelativeStandardCurveCreator,
            genotyping.GenotypingCreator,
            melt_curve.MeltCurveCreator,
            presence_absence.PresenceAbsenceCreator,
        ]
        if creator.check_type(contents)
    ]

    if len(possible_creators) == 1:
        return possible_creators[0].create(contents)

    msg = f"Unable to infer experiment type from sheets in the input"
    raise AllotropeConversionError(msg)

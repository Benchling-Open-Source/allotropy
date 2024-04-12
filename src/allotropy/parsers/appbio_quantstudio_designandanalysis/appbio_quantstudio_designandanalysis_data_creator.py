from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Data,
    Header,
    WellList,
)


def create_data(contents: DesignQuantstudioContents) -> Data:
    experiment_type = Data.get_experiment_type(contents)
    header = Header.create(contents.header)
    wells = WellList.create(contents, header, experiment_type)

    return Data(
        header,
        wells,
        experiment_type,
    )

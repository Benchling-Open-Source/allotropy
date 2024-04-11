from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    AmplificationData,
    Data,
    Header,
    MeltCurveData,
    MulticomponentData,
    Result,
    WellList,
)


def create_data(contents: DesignQuantstudioContents) -> Data:
    amp_data = contents.get_non_empty_sheet("Amplification Data")
    multi_data = contents.get_non_empty_sheet_or_none("Multicomponent")
    results_data = contents.get_non_empty_sheet("Results")
    melt_curve_data = contents.get_non_empty_sheet_or_none("Melt Curve Raw")

    experiment_type = Data.get_experiment_type(contents)

    header = Header.create(contents.header)
    wells = WellList.create(results_data)

    for well in wells:
        if multi_data is not None:
            well.multicomponent_data = MulticomponentData.create(
                multi_data, well, header
            )

        for well_item in well.items.values():
            if melt_curve_data is not None:
                well_item.melt_curve_data = MeltCurveData.create(
                    melt_curve_data, well, well_item
                )

            well_item.amplification_data = AmplificationData.create(
                amp_data,
                well_item,
            )

            well_item.result = Result.create(
                results_data,
                well_item,
                experiment_type,
            )

    return Data(
        header,
        wells,
        experiment_type,
    )

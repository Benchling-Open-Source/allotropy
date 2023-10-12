from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_calculated_documents import (
    build_quantity,
    iter_calculated_data_documents,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Data,
    get_str,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    RawData,
    Result,
    WellList,
)
from allotropy.parsers.lines_reader import LinesReader


def create_data(reader: LinesReader) -> Data:
    header = Header.create(reader)
    wells = WellList.create(reader, header.experiment_type)
    raw_data = RawData.create(reader)

    amp_data = AmplificationData.get_data(reader)
    multi_data = MulticomponentData.get_data(reader)
    results_data, results_metadata = Result.get_data(reader)
    melt_data = MeltCurveRawData.get_data(reader)
    for well in wells:
        if multi_data is not None:
            well.multicomponent_data = MulticomponentData.create(multi_data, well)

        if melt_data is not None:
            well.melt_curve_raw_data = MeltCurveRawData.create(melt_data, well)

        for well_item in well.items.values():
            well_item.amplification_data = AmplificationData.create(amp_data, well_item)
            well_item.result = Result.create(
                results_data, well_item, header.experiment_type
            )

        if an_well_item := well.get_an_well_item():
            well.calculated_document = build_quantity(an_well_item)

    endogenous_control = get_str(results_metadata, "Endogenous Control") or ""
    reference_sample = get_str(results_metadata, "Reference Sample") or ""

    return Data(
        header,
        wells,
        raw_data,
        endogenous_control,
        reference_sample,
        list(
            iter_calculated_data_documents(
                wells,
                header.experiment_type,
                reference_sample,
                endogenous_control,
            )
        ),
    )

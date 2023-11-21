# mypy: disallow_any_generics = False

from io import StringIO

import pandas as pd

from allotropy.allotrope.models.cell_culture_analyzer_benchling_2023_09_cell_culture_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueMillimolePerLiter,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_reader import (
    RocheCedexBiohtReader,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import (
    Analyte,
    AnalyteList,
    Data,
    Sample,
    Title,
)


def get_data_stream() -> StringIO:
    title = [
        "0",
        "2021-06-01 13:04:06",
        "#ARC-FILE#",
        "1.1a",
        "2021-05-01",
        "2021-06-01",
        "CEDEX BIO HT",
        "620103",
        "6.0.0.1905 (1905)",
        "ADMIN",
    ]

    body = [
        [
            "40",
            "2021-05-20 16:55:51",
            "PPDTEST1",
            "",
            "SAM",
            "        ",
            "GLN2B",
            "        ",
            "mmol/L",
            " ",
            "  2.45",
            "  0.17138",
            "R",
        ],
        [
            "40",
            "2021-05-20 16:55:51",
            "PPDTEST1",
            "",
            "Sample",
            "        ",
            "NH3LB",
            "        ",
            "mmol/L",
            " ",
            "  1.846",
            "0",
            "R",
        ],
    ]
    title_text = "\t".join(title)
    body_text = "\n".join(["\t".join(row) for row in body])
    return StringIO("\n".join([title_text, body_text]))


def get_reader() -> RocheCedexBiohtReader:
    return RocheCedexBiohtReader(get_data_stream())


def get_reader_title() -> pd.Series:
    return pd.Series(
        {
            "row type": 0,
            "data processing time": "2021-06-01 13:04:06",
            "col3": "#ARC-FILE#",
            "col4": "1.1a",
            "col5": "2021-05-01",
            "col6": "2021-06-01",
            "model number": "CEDEX BIO HT",
            "device serial number": 620103,
            "col9": "6.0.0.1905 (1905)",
            "analyst": "ADMIN",
        }
    )


def get_reader_samples() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "row type",
            "measurement time",
            "sample identifier",
            "batch identifier",
            "sample role type",
            "col6",
            "analyte name",
            "col8",
            "concentration unit",
            "flag",
            "concentration value",
            "col12",
            "col13",
        ],
        data=[
            [
                40,
                "2021-05-20 16:55:51",
                "PPDTEST1",
                "",
                "Sample",
                "        ",
                "glutamine",
                "        ",
                "mmol/L",
                " ",
                2.45,
                0.17138,
                "R",
            ],
            [
                40,
                "2021-05-20 16:55:51",
                "PPDTEST1",
                "",
                "Sample",
                "        ",
                "ammonia",
                "        ",
                "mmol/L",
                " ",
                1.846,
                0,
                "R",
            ],
        ],
    )


def get_data() -> Data:
    return Data(
        title=Title(
            data_processing_time="2021-06-01 13:04:06",
            analyst="ADMIN",
            model_number="CEDEX BIO HT",
            device_serial_number="620103",
        ),
        samples=[
            Sample(
                name="PPDTEST1",
                role_type="Sample",
                measurement_time="2021-05-20 16:55:51",
                analyte_list=AnalyteList(
                    analytes=[
                        Analyte("ammonia", 1.846, "mmol/L"),
                        Analyte("glutamine", 2.45, "mmol/L"),
                    ],
                    molar_concentration_dict={
                        "ammonia": [
                            TNullableQuantityValueMillimolePerLiter(
                                value=1.846,
                            )
                        ],
                        "glutamine": [
                            TNullableQuantityValueMillimolePerLiter(
                                value=2.45,
                            )
                        ],
                    },
                    molar_concentration_nans={},
                    non_aggregrable_dict={},
                    non_aggregable_nans={},
                    num_measurement_docs=1,
                ),
            )
        ],
    )


def get_model() -> Model:
    return Model(
        measurement_aggregate_document=MeasurementAggregateDocument(
            measurement_identifier="",
            analyst="ADMIN",
            device_system_document=DeviceSystemDocument(
                device_identifier=None,
                model_number="CEDEX BIO HT",
                device_serial_number="620103",
            ),
            measurement_document=[
                MeasurementDocumentItem(
                    sample_document=SampleDocument(
                        sample_identifier="PPDTEST1",
                        batch_identifier=None,
                        sample_role_type="Sample",
                    ),
                    measurement_time="2021-05-20T16:55:51+00:00",
                    analyte_aggregate_document=AnalyteAggregateDocument(
                        analyte_document=[
                            AnalyteDocumentItem(
                                analyte_name="ammonia",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=1.846,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="glutamine",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=2.45,
                                ),
                            ),
                        ]
                    ),
                    pco2=None,
                    co2_saturation=None,
                    po2=None,
                    o2_saturation=None,
                    optical_density=None,
                    pH=None,
                    osmolality=None,
                    viability__cell_counter_=None,
                    total_cell_density__cell_counter_=None,
                    viable_cell_density__cell_counter_=None,
                    average_live_cell_diameter__cell_counter_=None,
                    average_total_cell_diameter__cell_counter_=None,
                    total_cell_diameter_distribution__cell_counter_=None,
                    viable_cell_count__cell_counter_=None,
                    total_cell_count__cell_counter_=None,
                )
            ],
            data_processing_time="2021-06-01T13:04:06+00:00",
        ),
        manifest="http://purl.allotrope.org/manifests/cell-culture-analyzer/BENCHLING/2023/09/cell-culture-analyzer.manifest",
    )

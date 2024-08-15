from __future__ import annotations

from io import StringIO

import pandas as pd

from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
    SolutionAnalyzerDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimolePerLiter,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Analyte,
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.roche_cedex_bioht.constants import SOLUTION_ANALYZER


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
            "2021-05-20 16:56:51",
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
        [
            "40",
            "2021-05-20 16:57:51",
            "PPDTEST1",
            "",
            "Sample",
            "        ",
            "ODB",
            "        ",
            "OD",
            " ",
            "  0.17138",
            "0",
            "R",
        ],
    ]
    title_text = "\t".join(title)
    body_text = "\n".join(["\t".join(row) for row in body])
    return StringIO("\n".join([title_text, body_text]))


def get_reader_title() -> pd.Series[str]:
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
            "software version": "6.0.0.1905 (1905)",
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
                "2021-05-20 16:56:51",
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
            [
                40,
                "2021-05-20 16:57:51",
                "PPDTEST1",
                "",
                "Sample",
                "        ",
                "optical_density",
                "        ",
                "OD",
                " ",
                0.17138,
                0,
                "R",
            ],
        ],
    )


def get_data() -> Data:
    return Data(
        metadata=Metadata(
            file_name="dummy.txt",
            device_type=SOLUTION_ANALYZER,
            software_name="CEDEX BIO HT",
            model_number="CEDEX BIO HT",
            equipment_serial_number="620103",
            software_version="6.0.0.1905 (1905)",
            device_identifier=NOT_APPLICABLE,
            unc_path="",
        ),
        measurement_groups=[
            MeasurementGroup(
                analyst="ADMIN",
                data_processing_time="2021-06-01 13:04:06",
                measurements=[
                    Measurement(
                        identifier="dummy_id",
                        measurement_time="2021-05-20 16:55:51",
                        sample_identifier="PPDTEST1",
                        absorbance=0.17138,
                    ),
                    Measurement(
                        identifier="dummy_id",
                        measurement_time="2021-05-20 16:55:51",
                        sample_identifier="PPDTEST1",
                        analytes=[
                            Analyte(
                                name="ammonia",
                                value=1.846,
                                unit="mmol/L",
                            ),
                            Analyte(
                                name="glutamine",
                                value=2.45,
                                unit="mmol/L",
                            ),
                        ],
                    ),
                ],
            )
        ],
    )


def get_model() -> Model:
    return Model(
        field_asm_manifest="http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest",
        solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
            solution_analyzer_document=[
                SolutionAnalyzerDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_document=[
                            MeasurementDocument(
                                measurement_identifier="dummy_id",
                                measurement_time="2021-05-20T16:55:51+00:00",
                                sample_document=SampleDocument(
                                    sample_identifier="PPDTEST1",
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type=SOLUTION_ANALYZER
                                        )
                                    ]
                                ),
                                absorbance=TQuantityValueMilliAbsorbanceUnit(
                                    value=0.17138,
                                    unit="mAU",
                                ),
                            ),
                            MeasurementDocument(
                                measurement_identifier="dummy_id",
                                measurement_time="2021-05-20T16:55:51+00:00",
                                sample_document=SampleDocument(
                                    sample_identifier="PPDTEST1",
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type=SOLUTION_ANALYZER
                                        )
                                    ]
                                ),
                                analyte_aggregate_document=AnalyteAggregateDocument(
                                    analyte_document=[
                                        AnalyteDocument(
                                            analyte_name="ammonia",
                                            molar_concentration=TQuantityValueMillimolePerLiter(
                                                value=1.846,
                                                unit="mmol/L",
                                            ),
                                        ),
                                        AnalyteDocument(
                                            analyte_name="glutamine",
                                            molar_concentration=TQuantityValueMillimolePerLiter(
                                                value=2.45,
                                                unit="mmol/L",
                                            ),
                                        ),
                                    ]
                                ),
                            ),
                        ],
                        data_processing_time="2021-06-01T13:04:06+00:00",
                    ),
                    analyst="ADMIN",
                )
            ],
            device_system_document=DeviceSystemDocument(
                model_number="CEDEX BIO HT",
                equipment_serial_number="620103",
                device_identifier=NOT_APPLICABLE,
            ),
            data_system_document=DataSystemDocument(
                file_name="dummy.txt",
                UNC_path="",
                software_name="CEDEX BIO HT",
                software_version="6.0.0.1905 (1905)",
                ASM_converter_name="allotropy_roche_cedex_bioht",
                ASM_converter_version=ASM_CONVERTER_VERSION,
            ),
        ),
    )

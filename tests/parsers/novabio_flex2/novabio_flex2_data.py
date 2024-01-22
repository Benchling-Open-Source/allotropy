from io import StringIO

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
    TNullableQuantityValueGramPerLiter,
    TNullableQuantityValueMillimeterOfMercury,
    TNullableQuantityValueMillimolePerLiter,
    TNullableQuantityValuePercent,
    TNullableQuantityValuePH,
)
from allotropy.parsers.novabio_flex2.constants import PROPERTY_MAPPINGS
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import (
    Analyte,
    Data,
    Sample,
    SampleList,
    Title,
)


def get_input_title() -> str:
    return "SampleResults2022-06-28_142558.csv"


def get_input_stream() -> StringIO:
    data = {
        "Date & Time": "6-24-2022  14:34:52",
        "Sample ID": "BP_R10_KP_008_D0",
        "Sample Type": "Spent Media",
        "Gln": "1.83",
        "Glu": "0.33",
        "Gluc": "2.65",
        "Lac": "0.18",
        "NH4+": "0.48",
        "Na+": "151.6",
        "K+": "4.22",
        "Ca++": "0.82",
        "pH": "7.400",
        "PO2": "191.6",
        "PCO2": "46.8",
        "Vessel ID": "3L Bioreactor",
        "Batch ID": "KP_008",
        "Cell Type": "Workhog",
        "Vessel Temperature (°C)": "37.0",
        "Vessel Pressure (psi)": "30.0",
        "Sparging O2%": "320.9",
        "Chemistry Dilution Ratio": "1:1",
        "pH @ Temp": "7.400",
        "PCO2 @ Temp": "46.8",
        "PO2 @ Temp": "191.6",
        "O2 Saturation": "100.0",
        "CO2 Saturation": "6.6",
        "HCO3": "29.3",
        "Chemistry Flow Time": "6.67",
        "pH / Gas Flow Time": "3.65",
        "Tray Location": "",
        "Time In Tray": "",
        "Sample Time": "24-6-2022  14:34:52",
        "Operator": "BioprocessingTeam",
        "": "",
    }
    return StringIO("\n".join([",".join(data.keys()), ",".join(data.values())]))


def get_data() -> Data:
    return Data(
        title=Title(
            processing_time="2022-06-28 142558",
            device_identifier=None,
        ),
        sample_list=SampleList(
            analyst="BioprocessingTeam",
            samples=[
                Sample(
                    identifier="BP_R10_KP_008_D0",
                    role_type="Spent Media",
                    measurement_time="2022-06-24T14:34:52",
                    batch_identifier="KP_008",
                    analytes=sorted(
                        [
                            Analyte.create("Gln", 1.83),
                            Analyte.create("Glu", 0.33),
                            Analyte.create("Gluc", 2.65),
                            Analyte.create("Lac", 0.18),
                            Analyte.create("NH4+", 0.48),
                            Analyte.create("Na+", 151.6),
                            Analyte.create("K+", 4.22),
                            Analyte.create("Ca++", 0.82),
                            Analyte.create("HCO3", 29.3),
                        ]
                    ),
                    properties={
                        "co2_saturation": PROPERTY_MAPPINGS["co2_saturation"]["cls"](
                            value=6.6
                        ),
                        "o2_saturation": PROPERTY_MAPPINGS["o2_saturation"]["cls"](
                            value=100.0
                        ),
                        "pH": PROPERTY_MAPPINGS["pH"]["cls"](value=7.4),
                        "po2": PROPERTY_MAPPINGS["po2"]["cls"](value=191.6),
                        "pco2": PROPERTY_MAPPINGS["pco2"]["cls"](value=46.8),
                    },
                )
            ],
        ),
    )


def get_model() -> Model:
    return Model(
        measurement_aggregate_document=MeasurementAggregateDocument(
            measurement_identifier="",
            analyst="BioprocessingTeam",
            device_system_document=DeviceSystemDocument(
                device_identifier=None,
                model_number="NovaBio Flex2",
                device_serial_number=None,
            ),
            measurement_document=[
                MeasurementDocumentItem(
                    sample_document=SampleDocument(
                        sample_identifier="BP_R10_KP_008_D0",
                        batch_identifier="KP_008",
                        sample_role_type="Spent Media",
                    ),
                    measurement_time="2022-06-24T14:34:52+00:00",
                    analyte_aggregate_document=AnalyteAggregateDocument(
                        analyte_document=[
                            AnalyteDocumentItem(
                                analyte_name="ammonium",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=0.48,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="bicarbonate",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=29.3,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="calcium",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=0.82,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="glucose",
                                molar_concentration=TNullableQuantityValueGramPerLiter(
                                    value=2.65,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="glutamate",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=0.33,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="glutamine",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=1.83,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="lactate",
                                molar_concentration=TNullableQuantityValueGramPerLiter(
                                    value=0.18,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="potassium",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=4.22,
                                ),
                            ),
                            AnalyteDocumentItem(
                                analyte_name="sodium",
                                molar_concentration=TNullableQuantityValueMillimolePerLiter(
                                    value=151.6,
                                ),
                            ),
                        ]
                    ),
                    pco2=TNullableQuantityValueMillimeterOfMercury(
                        value=46.8,
                    ),
                    co2_saturation=TNullableQuantityValuePercent(
                        value=6.6,
                    ),
                    po2=TNullableQuantityValueMillimeterOfMercury(
                        value=191.6,
                    ),
                    o2_saturation=TNullableQuantityValuePercent(
                        value=100.0,
                    ),
                    optical_density=None,
                    pH=TNullableQuantityValuePH(
                        value=7.4,
                    ),
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
            data_processing_time="2022-06-28T14:25:58+00:00",
        ),
        manifest="http://purl.allotrope.org/manifests/cell-culture-analyzer/BENCHLING/2023/09/cell-culture-analyzer.manifest",
    )

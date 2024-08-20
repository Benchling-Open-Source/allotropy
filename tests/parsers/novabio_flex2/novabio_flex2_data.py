from io import StringIO

from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Analyte,
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.novabio_flex2.constants import (
    DEVICE_TYPE,
    MODEL_NUMBER,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
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
        metadata=Metadata(
            file_name="SampleResults2022-06-28_142558.csv",
            device_type=DEVICE_TYPE,
            model_number=MODEL_NUMBER,
            product_manufacturer=PRODUCT_MANUFACTURER,
            device_identifier=None,
            software_name=SOFTWARE_NAME,
        ),
        measurement_groups=[
            MeasurementGroup(
                analyst="BioprocessingTeam",
                data_processing_time="2022-06-28 142558",
                measurements=[
                    Measurement(
                        identifier="dummy_id",
                        measurement_time="2022-06-24 14:34:52",
                        sample_identifier="BP_R10_KP_008_D0",
                        batch_identifier="KP_008",
                        description="Spent Media",
                        detection_type="metabolite-detection",
                        analytes=sorted(
                            [
                                Analyte("ammonium", 0.48, "mmol/L"),
                                Analyte("bicarbonate", 29.3, "mmol/L"),
                                Analyte("calcium", 0.82, "mmol/L"),
                                Analyte("glucose", 2.65, "g/L"),
                                Analyte("glutamate", 0.33, "mmol/L"),
                                Analyte("glutamine", 1.83, "mmol/L"),
                                Analyte("lactate", 0.18, "g/L"),
                                Analyte("potassium", 4.22, "mmol/L"),
                                Analyte("sodium", 151.6, "mmol/L"),
                            ]
                        ),
                    ),
                    Measurement(
                        identifier="dummy_id",
                        measurement_time="2022-06-24 14:34:52",
                        sample_identifier="BP_R10_KP_008_D0",
                        batch_identifier="KP_008",
                        description="Spent Media",
                        detection_type="blood-gas-detection",
                        po2=191.6,
                        pco2=46.8,
                        carbon_dioxide_saturation=6.6,
                        oxygen_saturation=100.0,
                    ),
                    Measurement(
                        identifier="dummy_id",
                        measurement_time="2022-06-24 14:34:52",
                        sample_identifier="BP_R10_KP_008_D0",
                        batch_identifier="KP_008",
                        description="Spent Media",
                        detection_type="ph-detection",
                        ph=7.4,
                        temperature=37.0,
                    ),
                ],
            )
        ],
    )

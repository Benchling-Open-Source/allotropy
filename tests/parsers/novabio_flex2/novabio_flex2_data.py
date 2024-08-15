from io import StringIO

from allotropy.parsers.novabio_flex2.constants import (
    BLOOD_GAS_DETECTION_MAPPINGS,
    PH_DETECTION_MAPPINGS,
)
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
                    sample_type="Spent Media",
                    measurement_time="2022-06-24 14:34:52",
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
                    blood_gas_properties={
                        "carbon_dioxide_saturation": BLOOD_GAS_DETECTION_MAPPINGS[
                            "carbon_dioxide_saturation"
                        ]["cls"](value=6.6),
                        "oxygen_saturation": BLOOD_GAS_DETECTION_MAPPINGS[
                            "oxygen_saturation"
                        ]["cls"](value=100.0),
                        "pO2": BLOOD_GAS_DETECTION_MAPPINGS["pO2"]["cls"](value=191.6),
                        "pCO2": BLOOD_GAS_DETECTION_MAPPINGS["pCO2"]["cls"](value=46.8),
                    },
                    ph_properties={
                        "pH": PH_DETECTION_MAPPINGS["pH"]["cls"](value=7.4),
                        "temperature": PH_DETECTION_MAPPINGS["temperature"]["cls"](
                            value=37.0
                        ),
                    },
                    cell_type_processing_method="Workhog",
                    cell_density_dilution_factor=None,
                    cell_counter_properties={},
                    osmolality_properties={},
                )
            ],
        ),
    )

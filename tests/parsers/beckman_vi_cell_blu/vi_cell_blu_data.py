import pandas as pd

from allotropy.allotrope.models.cell_counter_benchling_2023_09_cell_counter import (
    CellCountingAggregateDocument,
    CellCountingDocumentItem,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataDocument,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION


def get_filename() -> str:
    return "example.csv"


def get_data() -> pd.DataFrame:
    return pd.DataFrame(
        data=[
            [
                "Vi-CELL",
                "TF-B0256-EXPN-SF",
                "6.0",
                "30.0",
                "2022-03-21 16:56:00",
                "Mammalian",
                "1.0",
                "96.9",
                "0.78",
                "0.75",
                "18.51",
                "18.72",
                "2191.0",
                "2123.0",
                "0.88",
                "0.88",
            ]
        ],
        columns=[
            "Analysis by",
            "Sample ID",
            "Minimum Diameter (μm)",
            "Maximum Diameter (μm)",
            "Analysis date/time",
            "Cell type",
            "Dilution",
            "Viability (%)",
            "Total (x10^6) cells/mL",
            "Viable (x10^6) cells/mL",
            "Average diameter (μm)",
            "Average viable diameter (μm)",
            "Cell count",
            "Viable cells",
            "Average circularity",
            "Average viable circularity",
        ],
    )


def get_model() -> Model:
    data = get_data()
    filename = get_filename()
    sample = data.loc[0]
    return Model(
        cell_counting_aggregate_document=CellCountingAggregateDocument(
            device_system_document=DeviceSystemDocument(
                model_number="Vi-Cell BLU",
            ),
            data_system_document=DataSystemDocument(
                file_name=filename,
                software_name="Vi-Cell BLU",
                ASM_converter_name=ASM_CONVERTER_NAME,
                ASM_converter_version=ASM_CONVERTER_VERSION,
            ),
            cell_counting_document=[
                CellCountingDocumentItem(
                    analyst=sample.get("Analysis by"),  # type: ignore[arg-type]
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="",
                                measurement_time="2022-03-21T16:56:00+00:00",
                                sample_document=SampleDocument(sample_identifier=sample.get("Sample ID")),  # type: ignore[arg-type]
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="brightfield imager (cell counter)",
                                            detection_type="brightfield",
                                        )
                                    ]
                                ),
                                processed_data_document=ProcessedDataDocument(
                                    data_processing_document=DataProcessingDocument(
                                        cell_type_processing_method=sample.get("Cell type"),  # type: ignore[arg-type]
                                        minimum_cell_diameter=TQuantityValueMicrometer(
                                            value=sample.get("Minimum Diameter (μm)"),  # type: ignore[arg-type]
                                        ),
                                        maximum_cell_diameter=TQuantityValueMicrometer(
                                            value=sample.get("Maximum Diameter (μm)"),  # type: ignore[arg-type]
                                        ),
                                        cell_density_dilution_factor=TQuantityValueUnitless(
                                            value=sample.get("Dilution"),  # type: ignore[arg-type]
                                        ),
                                    ),
                                    viability__cell_counter_=TQuantityValuePercent(
                                        value=sample.get("Viability (%)"),  # type: ignore[arg-type]
                                    ),
                                    viable_cell_density__cell_counter_=TQuantityValueMillionCellsPerMilliliter(
                                        value=sample.get("Viable (x10^6) cells/mL"),  # type: ignore[arg-type]
                                    ),
                                    total_cell_count=TQuantityValueCell(
                                        value=sample.get("Cell count"),  # type: ignore[arg-type]
                                    ),
                                    total_cell_density__cell_counter_=TQuantityValueMillionCellsPerMilliliter(
                                        value=sample.get("Total (x10^6) cells/mL"),  # type: ignore[arg-type]
                                    ),
                                    average_total_cell_diameter=TQuantityValueMicrometer(
                                        value=sample.get("Average diameter (μm)"),  # type: ignore[arg-type]
                                    ),
                                    average_live_cell_diameter__cell_counter_=TQuantityValueMicrometer(
                                        value=sample.get("Average viable diameter (μm)"),  # type: ignore[arg-type]
                                    ),
                                    viable_cell_count=TQuantityValueCell(
                                        value=sample.get("Viable cells"),  # type: ignore[arg-type]
                                    ),
                                    average_total_cell_circularity=TQuantityValueUnitless(
                                        value=sample.get("Average circularity"),  # type: ignore[arg-type]
                                    ),
                                    average_viable_cell_circularity=TQuantityValueUnitless(
                                        value=sample.get("Average viable circularity"),  # type: ignore[arg-type]
                                    ),
                                ),
                            )
                        ],
                    ),
                )
            ],
        ),
    )

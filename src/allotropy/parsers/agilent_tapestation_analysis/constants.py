from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueKiloDalton,
    TQuantityValueNumber,
    TQuantityValueSecondTime,
)

NO_SCREEN_TAPE_ID_MATCH = "The ScreenTape ID associated with the sample {} does not match any ScreenTape element."

PEAK_UNIT_CLASSES = type[
    TQuantityValueKiloDalton | TQuantityValueNumber | TQuantityValueSecondTime
]

PEAK_UNIT_CLASS_LOOKUP: dict[str, PEAK_UNIT_CLASSES] = {
    "nt": TQuantityValueNumber,
    "bp": TQuantityValueNumber,
    "kD": TQuantityValueKiloDalton,
}

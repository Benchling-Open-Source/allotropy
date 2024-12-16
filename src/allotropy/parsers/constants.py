from allotropy.exceptions import AllotropeConversionError

NOT_APPLICABLE = "N/A"
# Used to fill an error value in a required ASM field.
NEGATIVE_ZERO = -0.0
# Used to fill in timestamp for required ASM fields when not available in source
DEFAULT_EPOCH_TIMESTAMP = "1970-01-01"

# Used to round well count to a reasonable number
POSSIBLE_WELL_COUNTS = [1, 2, 4, 6, 8, 12, 24, 48, 72, 96, 384, 1536, 3456]


def round_to_nearest_well_count(well_count: int) -> int | None:
    for possible_count in POSSIBLE_WELL_COUNTS:
        if well_count > possible_count:
            continue
        return possible_count
    return None


def get_well_count_by_well_ids(
    well_identifiers: list[int] | None = None, well_locations: list[str] | None = None
) -> int | None:
    if not well_identifiers and not well_locations:
        msg = "Must provide either well_identifiers or well_locations when determining plate size."
        raise AllotropeConversionError(msg)
    # Get well numbers via Well ID (1, 2, 3, ...) and well location (A1, B1, ...)
    well_number_by_ids = sorted(well_identifiers)[-1] if well_identifiers else 0
    well_number_by_position = 0
    if well_locations:
        largest_column = sorted([str(loc[0]) for loc in well_locations])[-1]
        largest_row = sorted(int(loc[1:]) for loc in well_locations)[-1]
        well_number_by_position = (
            ord(largest_column.upper()) - ord("A") + 1
        ) * largest_row
    largest_well_number = max(well_number_by_ids, well_number_by_position)
    if largest_well_number:
        return round_to_nearest_well_count(largest_well_number)
    return None

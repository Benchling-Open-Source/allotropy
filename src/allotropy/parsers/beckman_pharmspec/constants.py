PHARMSPEC_SOFTWARE_NAME = "PharmSpec"
DEVICE_TYPE = "solution-analyzer"

# This map is used to map the column names to units, for calculated data items.
UNIT_LOOKUP = {
    "particle_size": "µm",
    "cumulative_count": "(unitless)",
    "cumulative_particle_density": "Counts/mL",
    "differential_particle_density": "Counts/mL",
    "differential_count": "(unitless)",
}
VALID_CALCS = ["Average"]

REQUIRED_DISTRIBUTION_DOCUMENT_KEYS = [
    "particle_size",
    "cumulative_count",
    "cumulative_particle_density",
    "differential_particle_density",
    "differential_count",
]

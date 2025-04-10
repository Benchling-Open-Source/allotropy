Base schema: None

This is a proposed new schema for flow-cytometry devices.

* Changed mAU unit to second time for vertex document coordinates BENCHLING/2025/03
 * Reasoning: Added for handling cases where coordinates are measured in time units
 * Proposal: change mAU to s
* Added sum of squares role in the StatisticDatum class
 * Reasoning: Required for BD Biosciences FACSDiva parser to represent sum of squares calculations in data
 * Proposal: add sum of squares role to StatisticDatum class
* Added experiment identifier field to the measurement aggregate document
 * Reasoning: Required to represent experiment identifiers in flow cytometry data (AFR_0002009)
 * Proposal: add experiment identifier field to measurement aggregate document
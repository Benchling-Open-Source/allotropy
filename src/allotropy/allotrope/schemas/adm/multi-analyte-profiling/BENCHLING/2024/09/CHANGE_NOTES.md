Base schema: "http://purl.allotrope.org/json-schemas/adm/multi-analyte-profiling/REC/2024/09/multi-analyte-profiling.schema"

Changes:

* Added "calibration aggregate document"/"calibration document" to "device system document"
  * Reasoning: Utilized to record results of system suitability tests returned along with the assay data
  * Proposal: Proposed extension to the model submitted to Allotrope - incorporation blocked by resolution on the semantics of "calibration"


* Remove requirement for "fluorescence" field in analyte document
  * Reasoning: Utilization of fluorescence field for analyte statistics will instead be implemented in statistics document
  * Proposal: Remove requirement for "fluorescence" field in analyte document

* Add "method version", "measurement aggregate document" class
  * Reasoning: These should be included in REC/2024/12 core schema
  * Proposal: Add "method version" to measurement aggregate document

* Add "coefficient of variation role", "trimmed mode value role", "trimmed count role", "trimmed standard deviation role", "trimmed arithmetic mean role" to tStatisiticDatumRole class
  * Reasoning: Support of additional statistical terms that are exported from multi-analyte-profilers
  * Proposal: Add "coefficient of variation role", "trimmed mode value role", "trimmed count role", "trimmed standard deviation role", "trimmed arithmetic mean role" to tStatisiticDatumRole

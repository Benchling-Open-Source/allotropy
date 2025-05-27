Base schema: "http://purl.allotrope.org/json-schemas/adm/multi-analyte-profiling/REC/2024/09/multi-analyte-profiling.schema"

Changes:

* Added "calibration aggregate document"/"calibration document" to "device system document"
  * Reasoning: Utilized to record results of system suitability tests returned along with the assay data
  * Proposal: Proposed extension to the model submitted to Allotrope - incorporation blocked by resolution on the semantics of "calibration"


* Remove requirement for "fluorescence" field in analyte document
  * Reasoning: Utilization of fluorescence field for analyte statistics will instead be implemented in statistics document
  * Proposal: Remove requirement for "fluorescence" field in analyte document
Base schema: http://purl.allotrope.org/json-schemas/adm/electrophoresis/REC/2024/09/electrophoresis.embded.schema

Changes:

* Added "analytical method identifier" to technique document/measurement aggregate document
  * Added "experimental data identifier" to technique document/measurement aggregate document
  * Added "method version" to technique document/measurement aggregate document
  * Reasoning: These should have been included in REC/2024/06 electrophoresis schema from original proposal
  * Proposal: Add "analytical method identifier", "experimental data identifier", "method version" to technique document/measurement aggregate document

* Added "compartment temperature" to absorbance-point-detector/absorbance-cube-detector/fluorescence-point-detector measurement document
  * Reasoning: This should have been included in REC/2024/06 electrophoresis schema from original proposal
  * Proposal: Add "compartment temperature" to electrophoresis measurement schemas

* Added "location identifier" to technique document/sample document
  * Reasoning: This should have been included in REC/2024/06 electrophoresis schema from original proposal
  * Proposal: Add "location identifier" to technique document/sample document

* Added "peak name" to peak
* Added "peak position" to peak
* Added "relative corrected peak area" to peak
* Added "comment" to peak
  * Reasoning: This should have been included in REC/2024/06 electrophoresis schema from original proposal
  * Proposal: Add "peak name", "peak position", "relative corrected peak area", "comment" to peak

* Added TQuantityValueNumber and TQuantityValueKiloDalton units for "peak position", "peak end", "relative peak height", "peak start"

* Added "processed data aggregate document" to fluorescence-cube-detector measurementDocumentItems definition
  * Reasoning: "processed data aggregate document" was excluded from REC/2024/09 schema in fluorescence-cube-detector measurementDocumentItems definition, should be included as parent document to "processed data document"
  * Proposal: Add "processed data aggregate document" to fluorescence-cube-detector measurementDocumentItems, raise https://gitlab.com/allotrope-public/asm/-/issues/7 with Allotrope on missing from REC/2024/09

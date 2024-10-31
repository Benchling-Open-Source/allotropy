Base schema: http://purl.allotrope.org/json-schemas/adm/plate-reader/REC/2024/09/plate-reader.schema

Changes:

* Added "analytical method identifier" to technique document/measurement aggregate document
  * Added "experimental data identifier" to technique document/measurement aggregate document
  * Added "method version" to technique document/measurement aggregate document
  * Reasoning: These should have been included in REC/2024/06 electrophoresis schema from original proposal
  * Proposal: Add "analytical method identifier", "experimental data identifier", "method version" to technique document/measurement aggregate document

* Added "location identifier" to technique document/sample document
  * Reasoning: This should have been included in REC/2024/06 electrophoresis schema from original proposal
  * Proposal: Add "location identifier" to technique document/sample document

* Added "processed data aggregate document" to fluorescence-cube-detector & luminescence-cube-detector measurementDocumentItems definition
  * Reasoning: "processed data aggregate document" was excluded from REC/2024/09 schema in fluorescence-cube-detector measurementDocumentItems definition, should be included as parent document to "processed data document"
  * Proposal: Add "processed data aggregate document" to fluorescence-cube-detector measurementDocumentItems, raise https://gitlab.com/allotrope-public/asm/-/issues/7 with Allotrope on missing from REC/2024/09
  
* Added optical-imaging-fluorescence-point-detector measurementDocumentItems to Plate Reader available measurement schemas
  * Reasoning: Add fluorescent optical imaging support to measurement documents for Plate Reader instrument software's with fluorescent imaging functionality
  * Proposal: Added optical-imaging-fluorescence-point-detector measurementDocumentItems to Plate Reader available measurement schemas

* Added optical-imaging-transmitted-light-point-detector measurementDocumentItems to Plate Reader available measurement schemas
  * Reasoning: Add transmitted light optical imaging support to measurement documents for Plate Reader instrument software's with transmitted light imaging functionality
  * Proposal: Added optical-imaging-transmitted-light-point-detector measurementDocumentItems to Plate Reader available measurement schemas
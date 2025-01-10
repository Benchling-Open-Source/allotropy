Base schema: http://purl.allotrope.org/json-schemas/adm/liquid-chromatography/REC/2023/09/liquid-chromatography.schema

Changes:

* Added fluorescence-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas
  * Reasoning: Extend support for fluorescence chromatogram data within liquid-chromatography schema
  * Proposal: Added fluorescence-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas
* Changed "elapsed time" dimension to "retention time" in chromatogram data cube of fluorescence-cube-detector measurementDocumentItems
  * Reasoning: Chromatogram data cube reports dimension in retention time
  * Proposal: Change dimension from "elapsed time" to "retention time"

* Added pH-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas
  * Reasoning: Extend support for pH chromatogram data within liquid-chromatography schema
  * Proposal: Added pH-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas REC/2024/12

* Added temperature-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas
  * Reasoning: Extend support for temperature profile data within liquid-chromatography schema device control document
  * Proposal: Add temperature-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas

* Added pressure-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas
  * Reasoning: Extend support for sample/column pressure data within liquid-chromatography schema device control document
  * Proposal: Add pressure-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas

* Added flow-rate-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas
  * Reasoning: Extend support for sample/system flow rate data within liquid-chromatography schema device control document
  * Proposal: Add flow-rate-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas

* Added solvent-concentration-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas
  * Reasoning: Extend support for solvent concentration data within liquid-chromatography schema device control document
  * Proposal: Add solvent-concentration-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas

* Added % conductivity chromatogram data cube to conductivity-detector measurement schema under processed data document
  * Reasoning: Added for handling of processed % conductivity data
  * Proposal: Add % conductivity chromatogram data cube to conductivity-detector measurement schema under processed data document

* Added data system document to REC/2023/09 hierarchy schema
  * Reasoning: This has been added in future versions, adding for data system metadata recording
  * Proposal: Add data system document to REC/2023/09 hierarchy schema

* Added CV/h (Column Volume per Hour) to REC/2023/09 units schema
  * Reasoning: Added for handling of sample flow rate data cube and system flow rate data cube support
  * Proposal: CV/h (Column Volume per Hour) to REC/2023/09 units schema.
  
* Added "processed data aggregate document" to uv-absorbance-cube-detection, uv-absorbance-spectrum-detection, conductivity-cube-detection measurementDocumentItems definition
  * Reasoning: "processed data aggregate document" was excluded from REC/2023/09 schema in uv-absorbance-cube-detection, uv-absorbance-spectrum-detection, conductivity-cube-detection measurementDocumentItems definition, should be included as parent document to "processed data document"
  * Proposal: Add "processed data aggregate document" to uv-absorbance-cube-detection, uv-absorbance-spectrum-detection, conductivity-cube-detection measurementDocumentItems
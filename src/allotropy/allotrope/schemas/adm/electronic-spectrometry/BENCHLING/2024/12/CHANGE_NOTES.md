Base schema: http://purl.allotrope.org/json-schemas/adm/electronic-spectrometry/REC/2024/09/electronic-spectrometry.embed.schema

Changes:

* Added "analytical method identifier" to technique document/measurement aggregate document
* Added "experimental data identifier" to technique document/measurement aggregate document
* Added "method version" to technique document/measurement aggregate document
  * Reasoning: These should be included in REC/2024/12 core schema
  * Proposal: Add "analytical method identifier", "experimental data identifier", "method version" to technique document/measurement aggregate document

* Added "location identifier" to technique document/sample document
  * Reasoning: These should be included in REC/2024/12 core schema
  * Proposal: Add "location identifier" to technique document/sample document

* Added "transmittance" to absorbance-point-detector measurement schema
  * Reasoning: Added to support transmittance measurements in absorbance reads
  * Proposal: Added "transmittance" to absorbance-point-detector measurement schema

* Added absorbance-spectrum-detector measurementDocumentItems to electronic-spectrometry measurement schemas
  * Reasoning: Added to support absorbance/transmittance spectral scan data
  * Proposal: Added absorbance-spectrum-detector measurementDocumentItems to electronic-spectrometry measurement schemas

* Added fluorescence-spectrum-detector measurementDocumentItems to electronic-spectrometry measurement schemas
  * Reasoning: Added to support fluorescence excitation/emission spectral scan data
  * Proposal: Added fluorescence-spectrum-detector measurementDocumentItems to electronic-spectrometry measurement schemas
Base schema: http://purl.allotrope.org/json-schemas/adm/pcr/REC/2023/09/qpcr.schema

TODO: update to "http://purl.allotrope.org/json-schemas/adm/pcr/REC/2024/06/qpcr.schema"
TODO: update to "http://purl.allotrope.org/json-schemas/adm/pcr/REC/2024/06/dpcr.schema"

Changes:

* Added "data system document" to "qPCR aggregate document"
  * Reasoning: Extension adopted in order to capture metadata about the originating computer system, software, file, and ASM conversion
  * Proposal: add "data system document" to ASM technique documents
  * Note: This has been implemented in the 2024/06 release of the core schema

* Removed "device document" from "device system document"
  * Reasoning: contents of "device document" are covered in other documents
    * All fields are covered between "device system document" and "device control document"
  * Proposal: TODO these should be added back to conform with ASM since they are optional.

* Removed "product manufacturer", "brand name", "equipment serial number", "model number", "firmware version" from "device control document" in favor of "device system document"
  * Reasoning: these fields are covered in "device system document"
  * Proposal: TODO these should be added back to conform with ASM since they are optional.

* Missing "processed data aggregate document" and "statistics aggregate document" from technique aggregate document
  * Reasoning: Not added during initial implementation while ASM was being figured out.
  * Proposal: TODO update supported schema to match ASM

* Missing "diagnostic trace aggregate document", "processed data aggregate document", "calculated data aggregate document", "statistics aggregate document" from technique document
  * Reasoning: Not added during initial implementation while ASM was being figured out.
  * Proposal: TODO update supported schema to match ASM

* Removed "written name", "vial location identifier", and "location identifier" from "sample document"
  * Reasoning: this was a bug
  * Proposal: TODO fix bug by adding them to conform with ASM

* Changed type of "sample role type" to tStringValue, from enum
  * Reasoning: this is a bug
  * Proposal: TODO fix bug to conform to ASM

* Added properties for "data processing document"
  * Reasoning: "reference DNA description" and "reference sample description" were added to the "data processing document" within the "calculated document" to assist in the interpretation of the "calculated result"
  * Proposal: The core schema supports the use of a "data processing document" within the "calculated data document", however, the constituent fields are not declared. Declare these fields as optional.

* Added "target DNA description" as required on "measurement document"
  * Reasoning: Proposed change to ASM when developing the model, rejected and so does not reflect published ASM
  * Proposal: TODO adjust our schema to remove requirement and conform to ASM

* Added "processed data aggregate document" as required on "measurement document"
  * Reasoning: Proposed change to ASM when developing the model, rejected and so does not reflect published ASM
  * Proposal: TODO adjust our schema to remove requirement and conform to ASM

* Added "PCR detection chemistry" as required in "device control document"
  * Reasoning: Proposed change to ASM when developing the model, rejected and so does not reflect published ASM
  * Proposal: TODO adjust our schema to remove requirement and conform to ASM

* Removed "analyst" from required for "qPCR document"
  * Reasoning: Anaylst is not always provided by instruments.
  * Proposal: remove "analyst" from required for "qPCR document"
  * NOTE: This change has been proposed to Allotrope

* Removed required fields "data source identifier" and "data source feature" for "data source document"
  * Reasoning: these fields are required for interpreting data source document
  * Proposal: add these fields as required in the ASM schema

* Fields that were renamed from our originally proposed schema to the accepted version
  * Proposal: TODO implement these name changes to confirm with ASM
  * Changes:
    * Renamed "cycle threshold value setting (qPCR)" to "cycle threshold value setting"
    * Renamed "genotyping qPCR method identifier" to "genotyping determination method"
    * Renamed "genotyping qPCR method setting (qPCR)" to "genotyping determination method setting"
    * Renamed "cycle threshold result (qPCR)" to "cycle threshold result"
    * Renamed "genotyping qPCR result" to "genotyping determination result"
    * Renamed "qPCR detection chemistry" to "PCR detection chemistry"
    * Renamed "equipment serial number" to "device serial number" in "device system document"
    * Renamed "denaturing duration setting" to "denaturing time setting"
    * Renamed "annealing duration setting" to "annealing time setting"
    * Renamed "primer extension temperature setting" to "extension temperature setting"
    * Renamed "primer extension duration setting" to "extension time setting"

Base schema: http://purl.allotrope.org/json-schemas/adm/pcr/REC/2023/09/qpcr.schema

Changes:

* Added "data system document" to "qPCR aggregate document"
  * Reasoning: TODO
  * Proposal: add "data system document" to ASM technique documents

* Removed "device document" from "device system document"
  * Reasoning: contents of "device document" are covered in other documents
    * All fields are covered between "device system document" and "device control document"
  * Proposal: remove "device document" from "device system document"

* Removed "product manufacturer", "brand name", "equipment serial number", "model number", "firmware version" from "device control document" in favor of "device system document"
  * Reasoning: these fields are covered in "device system document"
  * Proposal: remove these fields from "device control document"

* Missing "processed data aggregate document" and "statistics aggregate document" from technique aggreagete document
  * Reasoning: Not added during initial implementation while ASM was being figured out.
  * Proposal: No change to ASM - update supported schema to match ASM

* Missing "diagnostic trace aggregate document", "processed data aggregate document", "calculated data aggregate document", "statistics aggregate document" from technique document
  * Reasoning: Not added during initial implementation while ASM was being figured out.
  * Proposal: No change to ASM - update supported schema to match ASM

* Removed "written name", "vial location identifier", and "location identifier" from "sample document"
  * Reasoning: TODO - bug?
  * Proposal: TODO

* Changed type of "sample role type" to tStringValue, from enum
  * Reasoning: TODO - bug?
  * Proposal: TODO

* Added properties for "data processing document"
  * Reasoning: TODO
  * Proposal: TODO

* Added "target DNA description" as required on "measurement document"
  * Reasoning: TODO
  * Proposal: add "target DNA description" as required on "measurement document"

* Added "processed data aggregate document" as required on "measurement document"
  * Reasoning: TODO
  * Proposal: add "processed data aggregate document" as required on "measurement document"

* Added "PCR detection chemistry" as required in "device control document"
  * Reasoning: TODO
  * Proposal: add "PCR detection chemistry" as required in "device control document"

* Removed "analyst" from required for "qPRC document"
  * Reasoning: TODO
  * Proposal: removed "analyst" from required for "qPRC document"

* Removed required fields "data source identifier" and "data source feature" for "data source document"
  * Reasoning: TOOD - bug?

* Renaming related to strategy of splitting of PRC document into qPRC and dPRC documents (see 2023/12 schemas)
  * Reasoning: TODO
  * Proposal: implement these name changes
  * Changes:
    * Renamed "cycle threshold value setting (qPCR)" to "cycle threshold value setting"
    * Renamed "genotyping qPCR method identifier" to "genotyping determination method"
    * Renamed "genotyping qPCR method setting (qPCR)" to "genotyping determination method setting"
    * Renamed "cycle threshold result (qPCR)" to "cycle threshold result"
    * Renamed "genotyping qPCR result" to "genotyping determination result"
    * Renamed "qPCR detection chemistry" to "PCR detection chemistry"

* Renamed "equipment serial number" to "device serial number" in "device system document"
  * Reasoning: TODO
  * Proposal: reaplce "equipment serial number" with "device serial number" in "device system document"

* Renamed "denaturing duration setting" to "denaturing time setting"
  * Reasoning: TODO
  * Proposal: TODO

* Renamed "annealing duration setting" to "annealing time setting"
  * Reasoning: TODO
  * Proposal: TODO

* Renamed "primer extension temperature setting" to "extension temperature setting"
  * Reasoning: TODO
  * Proposal: TODO

* Renamed "primer extension duration setting" to "extension time setting"
  * Reasoning: TODO
  * Proposal: TODO

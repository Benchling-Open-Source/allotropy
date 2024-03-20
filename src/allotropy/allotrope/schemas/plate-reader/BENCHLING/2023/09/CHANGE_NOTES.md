Base schema: http://purl.allotrope.org/json-schemas/adm/plate-reader/REC/2023/09/plate-reader.schema

Changes:

* Removed "asset management identifier" from required in "device system document"
  * Reasoning: This never should have been required, this was a bug in the initially published ASM schema
  * Proposal: remove "asset management identifier" from required in "device system document"
  * NOTE: this is implemented in 2023/12 version of plate-reader schema

* Removed "compartment temperature" from required in "measurement document"
  * Reasoning: not all instruments provide compartment temperature
  * Proposal: remove "compartment temperature" from required in "measurement document"
  * NOTE: this is implemented in 2023/12 version of plate-reader schema

* Added "data system document" to technique aggregate document
  * Reasoning: Extension adopted in order to capture metadata about the originating computer system, software, file, and ASM conversion
  * Proposal: add "data system document" to technique aggregate documents

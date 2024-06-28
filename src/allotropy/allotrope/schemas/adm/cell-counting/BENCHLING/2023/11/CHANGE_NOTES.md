Base schema: http://purl.allotrope.org/json-schemas/adm/cell-counting/REC/2023/09/cell-counting.schema

Changes:

* Removed "asset management identifier" from required in "device system document"
  * Reasoning: This never should have been required, this was a bug in the initially published ASM schema
  * Proposal: remove "asset management identifier" from required in "device system document"
  * NOTE: this is implemented in 2023/12 version of cell-counting schema

* Added "data system document" to "cell counting aggregate document"
  * Reasoning: Extension adopted in order to capture metadata about the originating computer system, software, file, and ASM conversion
  * Proposal: add "data system document" to ASM technique documents
  * Note: this is implemented in the 2024/06 release of the core schema

* Removed "total cell count" from required in "processed data document"
  * Reasoning: Not all cell counters provide total cell count
  * Proposal: remove "total cell count" from required in "processed data document", see https://gitlab.com/allotrope/adm/-/issues/610
  * NOTE: this is implemented in the 2023/12 release of cell-counting schema

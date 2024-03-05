Base schema: http://purl.allotrope.org/json-schemas/adm/cell-counting/REC/2023/09/cell-counting.schema

Changes:

* Removed "asset management identifier" from required in "device system document"
  * Reasoning: TODO
  * Proposal: remove "asset management identifier" from required in "device system document"
  * NOTE: this is implemented in 2023/12 version of cell-counting schema

* Added "data system document" to "cell counting aggregate document"
  * Reasoning: TODO
  * Proposal: add "data system document" to ASM technique documents

* Removed "device control document" from required in "device control aggregate document"
  * Reasoning: TODO - or is this a mistake?
  * Proposal: remove "device control document" from required in "device control aggregate document"

* Removed "total cell count" from required in "processed data document"
  * Reasoning: TODO, https://github.com/Benchling-Open-Source/allotropy/pull/136/commits/8cd79d264efba0f6d208b36415f7209c7a0b9e19
  * Proposal: remove "total cell count" from required in "processed data document"

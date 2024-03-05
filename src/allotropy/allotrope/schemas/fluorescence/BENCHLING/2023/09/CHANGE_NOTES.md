DEPRECATED - TO NOT USE. This is replaced by plate-reader/BENCHLING/2023/09/plate-reader.json

Base schema: http://purl.allotrope.org/json-schemas/adm/fluorescence/REC/2023/03/fluorescence-endpoint.schema

Changes:

* Removed "device type" from required in "device control document"
  * Reasoning: TODO
  * Proposal: remove "device type" from required in "device control document"

* Replaced "fluorescence" in "measurement document" with "data cube"
  * Reasoning: TODO
  * Proposal: use data cubes to store fluorescence measurements

* Added "processed data aggregate document" to "measurement document"
  * Reasoning: TODO
  * Proposal: add "processed data aggregate document" to "measurement document"

* Removed "measurement time" from required in "measurement aggregate document"
  * Reasoning: TODO
  * Proposal: remove "measurement time" from required in "measurement aggregate document"

DEPRECATED - DO NOT USE. This is replaced by plate-reader/BENCHLING/2023/09/plate-reader.json

Base schema: http://purl.allotrope.org/json-schemas/adm/ultraviolet-absorbance/REC/2023/03/ultraviolet-absorbance.schema

Changes:

* Removed "device type" from required in "device control document"
  * Reasoning: this is a bug
  * Proposal: TODO we should add back requirement
=
* Replaced "absorbance" in "measurement document" with "data cube"
  * Reasoning: this was a mistake in our initial implementation when we were first learning ASM
  * Proposal: no action needed, we should deprecate the use of this schema

* Added "processed data aggregate document" to "measurement document"
  * Reasoning: This is consistent with more modern ASM core schemas which optionally place a processed data doc in the measurement document.
  * Proposal: no action needed, as ASM core schema implements this now

* Removed "measurement time" from required in "measurement aggregate document"
  * Reasoning: some example files did not provide measurement times.
  * Proposal: no action needed, as ASM core schema implements this now

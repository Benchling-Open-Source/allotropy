Base schema: http://purl.allotrope.org/json-schemas/adm/binding-affinity-analyzer/WD/2024/12/binding-affinity-analyzer.embed.schema


Changes:

* Changed Nanomolar unit from "nmol/dm^3" to "nM"
  * Reasoning: To match other representations of molar concentration units
  * Proposal: update unit notation of Nanomolar from "nmol/dm^3" to "nM"
  * NOTE: proposed for adoption in the allotrope units.schema
  
* Added report point aggregate/report point document structure to processed data document of SPR detection schema for report point data
  * Reasoning: Remove parquet implementation of report point data for representation in ASM
  * Proposal: Add report point aggregate/report point document structure to remove parquet implementation
  * NOTE: proposed for adoption to binding affinity analyzer model in Allotrope

* Added sensorgram aggregate/sensorgram document structure to measurement document of SPR detection schema for sensorgram data
  * Reasoning: Remove parquet implementation of sensorgram data for representation in ASM, add in aggregate document/document structure for multiple sensorgrams in a single cycle
  * Proposal: Add sensorgram aggregate/sensorgram document structure to remove parquet implementation
  * NOTE: proposed for adoption to binding affinity analyzer model in Allotrope

* Added RU (response units) to units.schema for fields including relative response & absolute response
  * Reasoning: Add standardized units to units.schema for response units 
  * Proposal: Add RU (response units) to units.schema for fields including relative response & absolute response
  * NOTE: proposed for adoption in the allotrope units.schema

* Added RU/s (response units per second) to units.schema for calculated data field of slope
  * Reasoning: Add standardized units to units.schema for response units per second
  * Proposal: Add RU/s (response units per second) to units.schema for calculated data field of slope
  * NOTE: proposed for adoption in the allotrope units.schema
Base schema: None

The most recent schema for cell culture analyzers is http://purl.allotrope.org/json-schemas/adm/cell-culture-analyzer/REC/2021/12/cell-culture-analyzer.schema, and is quite out of date with the more modern schemas that implement "measurement aggregate document"

This was a proposed new schema for cell culture analyzers that is more in line with these more modern schemas.

Allotrope has deprecated cell-culture-analyzer models in favor of "solution analyzer" models: https://gitlab.com/allotrope/adm/-/blob/develop/purl/json-schemas/adm/solution-analyzer/REC/2023/12/solution-analyzer.schema.json

We will update parser to use this model instead in the future.

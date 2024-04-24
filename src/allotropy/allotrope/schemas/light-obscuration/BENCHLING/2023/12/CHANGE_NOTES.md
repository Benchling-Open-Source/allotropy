Base schema: http://purl.allotrope.org/json-schemas/adm/light-obscuration/REC/2021/12/light-obscuration.schema

Changes:

- New

  - Documents
    - Light Obscuration Aggregate Document
      - Data System Document
      - Device System Document
        - Device Document
      - Light Obscuration Document
        - Measurement Aggregate Document
          - Measurement Document
            - Device Control Aggregate Document
              - Device Control Document
              - Device Control Document Item
            - Sample Document
            - Processed Data Aggregate Document
              - Processed Data Document
      - Calculated Data Aggregate Document
        - Calculated Data Document
          - Data Source Aggregate Document
            - Data Source Document
  - Properties
    - Distibution Document/Distribution/Distribution Identifier

- Updated
  - Moved Measurement Document under Measurement Aggregate Document
  - Moved detector view volume from root to Device Control Document Item
  - Moved Distribution Document under Distribution Aggregate Document
  - Removed Differential Particle Density and Differential Count from required properties of Distribution
  -

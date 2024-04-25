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
  - Analyst moved to Measurement Aggregate Document properties
  - Measurement Document moved to Measurement Aggregate Document properties
  - Measurement Identifier moved to Measurement Document properteis
  - Distribution Document moved to Distribution Aggregate Document properties
  - Differential Particle Density and Differential Count removed from required properties of Distribution
  - Detector View Volume moved to Device Control Document Item properties
  - Detector View Volume moved to Device Control Document Item properties
  - Flush Volume Setting moved to Device Control Document Item properties
  - Repetition Setting moved to Device Control Document Item properties
  - Sample Volume Setting moved to Device Control Document Item properties
  - Dilution Factor Setting moved to Data Processing Document properties
  - Sample Identifier moved to Sample Document properties
  - Detector Identifier moved to Device Document properties
  - Detector Model Number moved to Device Document properties
  - Equipment Serial Number moved to Light Obscuration Aggregate Document properties
  - Model Number moved to Light Obscuration Aggregate Document properties
  - Measurement Time moved to Measurement Document properties

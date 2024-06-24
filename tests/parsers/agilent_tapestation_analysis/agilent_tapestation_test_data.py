import xml.etree.ElementTree as ET  # noqa: N817


def get_metadata_xml(
    rine_version: str | None = None,
    din_version: str | None = None,
    molecular_weight_unit: str = "nt",
) -> ET.Element:
    method_version = ""
    if rine_version:
        method_version = f"<RINeVersion>{rine_version}</RINeVersion>"
    elif din_version:
        method_version = f"<DINVersion>{din_version}</DINVersion>"

    xml_str = f"""
    <File>
        <FileInformation>
            <FileName>C:\\cfDNA-Tubes-16.cfDNA</FileName>
            <Assay>cfDNA</Assay>
            {method_version}
        </FileInformation>
        <ScreenTapes>
            <ScreenTape>
                <Environment>
                    <Experimenter>TapeStation User</Experimenter>
                    <InstrumentType>65536</InstrumentType>
                    <InstrumentSerialNumber>DEDAB00201</InstrumentSerialNumber>
                    <Computer>TAPESTATIONPC</Computer>
                    <AnalysisVersion>3.2.0.22472</AnalysisVersion>
                </Environment>
            </ScreenTape>
        </ScreenTapes>
        <Assay>
            <Units>
                <MolecularWeightUnit>{molecular_weight_unit}</MolecularWeightUnit>
            </Units>
        </Assay>
    </File>
    """
    return ET.fromstring(xml_str)  # noqa: S314


def get_samples_xml(
    with_regions: bool = False,  # noqa: FBT001, FBT002
    with_calculated_data: bool = False,  # noqa: FBT001, FBT002
    sample_error: str = "",
) -> ET.Element:
    regions = "<Regions />"
    if with_regions:
        regions = """
        <Regions>
            <Region>
                <From>504</From>
                <To>1000</To>
                <AverageSize>395</AverageSize>
                <Concentration>1.11</Concentration>
                <PercentOfTotal>4.09</PercentOfTotal>
                <Area>0.13</Area>
                <Comment>Degraded</Comment>
                <IsAutoAddedRegion>True</IsAutoAddedRegion>
            </Region>
            <Region>
                <From>42</From>
                <To>3000</To>
                <AverageSize>1944</AverageSize>
                <Molarity>0.765</Molarity>
                <PercentOfTotal>3.17</PercentOfTotal>
                <Area>0.10</Area>
                <Comment>Partially Degraded</Comment>
                <IsAutoAddedRegion>True</IsAutoAddedRegion>
            </Region>
        </Regions>
        """

    xml_str = f"""
    <File>
    <ScreenTapes>
        <Notes>
        </Notes>
        <ScreenTape>
            <ScreenTapeID>ScreenTape01</ScreenTapeID>
            <ExpiryDate>2020-10-04T23:59:59</ExpiryDate>
            <ElectrophoresisTemp>26.4</ElectrophoresisTemp>
            <ElectrophoresisTime>205</ElectrophoresisTime>
            <TapeRunDate>2020-09-20T03:52:58-05:00</TapeRunDate>
        </ScreenTape>
    </ScreenTapes>
    <Samples>
        <Sample>
            <WellNumber>A1</WellNumber>
            <Comment>Ladder</Comment>
            <Concentration>{58.2 if with_calculated_data else ""}</Concentration>
            <Observations>Ladder</Observations>
            <Alert>{sample_error}</Alert>
            <ScreenTapeID>ScreenTape01</ScreenTapeID>
            <Peaks>
                <Peak>
                    <Area>1.00</Area>
                    <AssignedQuantity>{8.50 if with_calculated_data else ""}</AssignedQuantity>
                    <Comment>
                    </Comment>
                    <FromMW>68</FromMW>
                    <FromPercent>{80.6 if with_calculated_data else ""}</FromPercent>
                    <Height>261.379</Height>
                    <Molarity>{131 if with_calculated_data else ""}</Molarity>
                    <Size>100</Size>
                    <Number>-</Number>
                    <Observations>Lower Marker</Observations>
                    <PercentIntegratedArea>-</PercentIntegratedArea>
                    <PercentOfTotal>-</PercentOfTotal>
                    <ToMW>158</ToMW>
                    <ToPercent>{85.4 if with_calculated_data else ""}</ToPercent>
                </Peak>
                <Peak>
                    <Area>1.33</Area>
                    <CalibratedQuantity>{11.3 if with_calculated_data else ""}</CalibratedQuantity>
                    <Comment>
                    </Comment>
                    <FromMW>3812</FromMW>
                    <FromPercent>{41.1 if with_calculated_data else ""}</FromPercent>
                    <Height>284.723</Height>
                    <Size>8525</Size>
                    <Number>1</Number>
                    <Observations>
                    </Observations>
                    <PercentIntegratedArea>92.30</PercentIntegratedArea>
                    <PercentOfTotal>44.38</PercentOfTotal>
                    <RunDistance>{46.5 if with_calculated_data else ""}</RunDistance>
                    <ToMW>&gt;60000</ToMW>
                </Peak>
            </Peaks>
            {regions}
        </Sample>
    </Samples>
    </File>
    """
    return ET.fromstring(xml_str)  # noqa: S314

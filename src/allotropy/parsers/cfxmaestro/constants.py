DISPLAY_NAME = "cfxmaestro"
DEVICE_TYPE = "<some device type>"

    #PO added this below
PRODUCT_MANUFACTURER = "Bio-Rad"
SOFTWARE_NAME = "CFX Maestro"
ASM_CONVERTER_NAME = "<this adapter>"
ASM_CONVERTER_VERSION = ""
CONTAINER_TYPE = "qPCR Reaction Block"
CALCULATED_DATA_NAME = "Cq Mean"
PROCESSED_DATA_NAME = "Cq Std. Dev"

NOT_APPLICABLE = "N/A"
# Used to fill an error value in a required ASM field.
NEGATIVE_ZERO = -0.0

#Hard coded plate well count to 96 wells for now....will need to return with a function to decuce the number of wells in a plate
#Maybe use something like this...from AB QuantStudio
#plate_well_count_search = re.search("(96)|(384)", data[str, "Block Type"])
PLATE_WELL_COUNT = 96

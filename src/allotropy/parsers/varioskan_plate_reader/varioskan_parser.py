# from allotropy.parsers.vendor_parser import MapperVendorParser


# class VarioskanParser(MapperVendorParser[Data, Model]):
#     DISPLAY_NAME = "Varioskan"
#     RELEASE_STATE = ReleaseState.WORKING_DRAFT
#     SUPPORTED_EXTENSIONS = "xlsx"
#     SCHEMA_MAPPER = Mapper
#
#     def create_data(self, named_file_contents: NamedFileContents) -> Data:
#         contents = read_multisheet_excel(
#             named_file_contents.contents, engine="calamine"
#         )
#         return DataVarioskan.create(
#             sheet_data=contents, file_name=named_file_contents.original_file_name
#         )

from allotropy.parser_factory import Vendor


class TestIdGenerator:
    vendor: Vendor
    next_id: int = 0

    def __init__(self, vendor: Vendor) -> None:
        self.vendor = vendor

    def generate_id(self) -> str:
        current_id = f"TEST_{self.vendor.name}_{self.next_id}"
        self.next_id += 1
        return current_id

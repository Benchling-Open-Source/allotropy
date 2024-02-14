import uuid

from allotropy.parsers.utils.id_generator import IdGenerator


class UuidGenerator(IdGenerator):
    def generate_id(self) -> str:
        return str(uuid.uuid4())


_UUID_GENERATOR = UuidGenerator()


def get_id_generator() -> IdGenerator:
    return _UUID_GENERATOR

import uuid

from allotropy.parsers.utils.id_generator import IdGenerator


class _UuidGenerator(IdGenerator):
    def generate_id(self) -> str:
        return str(uuid.uuid4())


UUID_GENERATOR = _UuidGenerator()

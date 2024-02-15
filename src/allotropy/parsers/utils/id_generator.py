from abc import ABC, abstractmethod
import uuid


class IdGenerator(ABC):
    @abstractmethod
    def generate_id(self) -> str:
        raise NotImplementedError


class _UuidGenerator(IdGenerator):
    def generate_id(self) -> str:
        return str(uuid.uuid4())


__UUID_GENERATOR = _UuidGenerator()


def get_id_generator() -> IdGenerator:
    return __UUID_GENERATOR

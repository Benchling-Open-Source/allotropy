from abc import ABC, abstractmethod
import uuid


class IdGenerator(ABC):
    @abstractmethod
    def generate_id(self) -> str:
        raise NotImplementedError


class _RandomUuidGenerator(IdGenerator):
    def generate_id(self) -> str:
        return str(uuid.uuid4())


_ID_GENERATOR = _RandomUuidGenerator()


class _IdGeneratorFactory:
    def get_id_generator(self) -> IdGenerator:
        return _ID_GENERATOR


__ID_GENERATOR_FACTORY = _IdGeneratorFactory()


def random_uuid_str() -> str:
    return __ID_GENERATOR_FACTORY.get_id_generator().generate_id()

from abc import ABC, abstractmethod

from allotropy.parsers.utils.uuids import UUID_GENERATOR


class IdGenerator(ABC):
    @abstractmethod
    def generate_id(self) -> str:
        raise NotImplementedError


def get_id_generator() -> IdGenerator:
    return UUID_GENERATOR

from abc import ABC, abstractmethod


class IdGenerator(ABC):
    @abstractmethod
    def generate_id(self) -> str:
        raise NotImplementedError

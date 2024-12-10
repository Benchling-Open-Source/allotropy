from abc import abstractmethod


class Transformation:
    @abstractmethod
    def transform(self, data: tuple[float, ...]) -> tuple[float, ...]:
        pass


class Min2Sec(Transformation):
    def transform(self, data: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(element * 60 for element in data)


class MScm2Sm(Transformation):
    def transform(self, data: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(element / 10 for element in data)

from dataclasses import dataclass


@dataclass
class Measurement:
    uuid: str
    sid: str
    tid: str
    m: float
    sum: float
    mean: float

from dataclasses import dataclass


@dataclass
class Measurement:
    uuid: str
    sid: str
    tid: str
    m: float
    sum_: float
    mean: float

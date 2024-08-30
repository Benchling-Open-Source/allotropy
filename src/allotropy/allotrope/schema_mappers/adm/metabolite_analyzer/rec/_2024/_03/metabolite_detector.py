from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ParamSpec, TypeVar

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueGramPerLiter,
    TQuantityValueMilliliterPerLiter,
    TQuantityValueMillimolePerLiter,
)
from allotropy.exceptions import AllotropeConversionError

T = TypeVar("T")
AggDocumentClass = TypeVar("AggDocumentClass")
DocumentClass = TypeVar("DocumentClass")
DocumentClass1 = TypeVar("DocumentClass1")
Type = Callable[..., T]
P = ParamSpec("P")
P2 = ParamSpec("P2")


@dataclass(frozen=True)
class Analyte:
    name: str
    value: float
    unit: str

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Analyte):
            return False

        return self.name < other.name

    def create_analyte_document(self, doc_class: Type[DocumentClass]) -> DocumentClass:
        if self.unit == "g/L":
            return doc_class(
                analyte_name=self.name,
                mass_concentration=TQuantityValueGramPerLiter(value=self.value),
            )
        elif self.unit == "mL/L":
            return doc_class(
                analyte_name=self.name,
                volume_concentration=TQuantityValueMilliliterPerLiter(value=self.value),
            )
        elif self.unit == "mmol/L":
            return doc_class(
                analyte_name=self.name,
                molar_concentration=TQuantityValueMillimolePerLiter(value=self.value),
            )
        elif self.unit == "U/L":
            if self.name == "ldh":
                return doc_class(
                    analyte_name=self.name,
                    molar_concentration=TQuantityValueMillimolePerLiter(
                        value=self.value * 0.0167 if self.value > 0 else self.value
                    ),
                )
            else:
                msg = f"Invalid unit for {self.name}: {self.unit}"
                raise AllotropeConversionError(msg)

        msg = f"Invalid unit for analyte: {self.unit}, value values are: g/L, mL/L, mmol/L"
        raise AllotropeConversionError(msg)


@dataclass(frozen=True, kw_only=True)
class HasAnalyteAggregateDocument:
    analytes: list[Analyte]

    def create_analyte_aggregate_document(
        self, agg_doc: Type[AggDocumentClass], item_doc: Type[DocumentClass]
    ) -> AggDocumentClass:
        return agg_doc(
            analyte_document=[
                analyte.create_analyte_document(item_doc) for analyte in self.analytes
            ]
        )


@dataclass(frozen=True, kw_only=True)
class MetaboliteDetectorMixin(HasAnalyteAggregateDocument):
    def measurement_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "analyte_aggregate_document": self.create_analyte_aggregate_document(
                kwargs["analyte_agg_doc"], kwargs["analyte_item_doc"]
            ),
        }

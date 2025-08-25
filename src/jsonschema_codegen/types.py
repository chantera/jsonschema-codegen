from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

from jsonschema_codegen.exprs import TypeExpr

Schema = Mapping[str, Any]


@dataclass(frozen=True)
class Context:
    expr_name: str | None
    schema: Schema
    path: Sequence[str | int]


class Parser(Protocol):
    def parse(self, schema: Schema | bool, context: Context | None = None) -> TypeExpr | None: ...


Interpreter = Callable[[Parser, TypeExpr, Schema], TypeExpr]

import hashlib
import json
from dataclasses import InitVar, asdict, dataclass, field, fields
from functools import cached_property
from typing import Any, Union


class _MISSING_TYPE:
    def __repr__(self) -> str:
        return "<MISSING>"


MISSING = _MISSING_TYPE()


@dataclass(frozen=True)
class TypeExpr:
    name: str | None = field(default=None, kw_only=True)
    # metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if type(self) is TypeExpr:
            raise TypeError("TypeExpr cannot be instantiated directly")

    @property
    def hint(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class UndefinedType(TypeExpr):
    pass


Annotation = Union[str, TypeExpr, "ParameterizedAnnotation"]
ParameterizedAnnotation = tuple[Annotation, list[Annotation]]  # e.g., Union[int, float]


def _resolve_annotation(value: Annotation) -> str:
    if isinstance(value, tuple):
        type_annotation = _resolve_annotation(value[0])
        type_args_annotation = ", ".join(_resolve_annotation(v) for v in value[1])
        return f"{type_annotation}[{type_args_annotation}]"
    elif isinstance(value, TypeExpr):
        return value.hint
    else:
        return value


@dataclass(frozen=True)
class AnnotatedType(TypeExpr):
    value: Annotation = field(compare=False)

    @property
    def hint(self) -> str:
        return self.name or self.annotation

    @cached_property
    def annotation(self) -> str:
        return _resolve_annotation(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AnnotatedType):
            cmp_fields = [f.name for f in fields(self) if f.compare]
            self_fields = tuple(getattr(self, f) for f in cmp_fields)
            other_fields = tuple(getattr(other, f) for f in cmp_fields)
            return (self_fields == other_fields) and (self.annotation == other.annotation)
        return NotImplemented


@dataclass(frozen=True)
class UnionType(AnnotatedType):
    value: Annotation = field(init=False, compare=False)
    types: InitVar[list[TypeExpr]]

    def __post_init__(self, types):
        object.__setattr__(self, "value", ("typing.Union", types))


@dataclass(frozen=True)
class ObjectType(TypeExpr):
    fields: list["Field"] = field(default_factory=list)

    @cached_property
    def canonical_name(self) -> str:
        if not self.name and not self.fields:
            return "Object"

        attrs = {"name": self.name, "fields": {f.name: asdict(f) for f in self.fields}}
        return f"Object_{_hash(attrs)}"

    @property
    def identifier(self) -> str:
        # Use canonical_name for anonymous object type
        name = self.name or self.canonical_name
        if not name.isidentifier():
            raise ValueError(f"Invalid identifier: {name}")
        return name

    @property
    def hint(self) -> str:
        return self.identifier


@dataclass(frozen=True)
class Field:
    name: str
    type: TypeExpr
    default: Any = field(default=MISSING, kw_only=True)
    required: bool = field(default=False, kw_only=True)


@dataclass(frozen=True)
class EnumType(TypeExpr):
    members: list[str]
    # TODO: implement


def _hash(o: Any) -> str:
    s = _JSONEncoder(sort_keys=True).encode(o)
    s = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return s


class _JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, _MISSING_TYPE):
            return str(o)
        return super().default(o)

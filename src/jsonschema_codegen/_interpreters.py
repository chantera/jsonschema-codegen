from collections.abc import Mapping
from dataclasses import replace
from enum import Enum

from jsonschema_codegen.exceptions import InterpretError, NotSupportedError, SchemaError
from jsonschema_codegen.exprs import (
    AnnotatedType,
    Field,
    ObjectType,
    TypeExpr,
    UndefinedType,
    UnionType,
)
from jsonschema_codegen.types import Context, Parser, Schema


class SchemaType(str, Enum):
    _ANY = "any"
    OBJECT = "object"
    ARRAY = "array"
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NULL = "null"


def _get_type(schema: Schema, default: SchemaType = SchemaType._ANY) -> SchemaType:
    type_ = schema.get("type")
    if type_ is None:
        return default
    elif isinstance(type_, list):
        raise ValueError(f"multiple types are not supported: {type_}")
    return type_


def _any_type(name: str | None = None) -> TypeExpr:
    return AnnotatedType(name=name, value="typing.Any")


def _object_type(name: str | None = None) -> TypeExpr:
    return ObjectType(name=name)


def _array_type(name: str | None = None) -> TypeExpr:
    return AnnotatedType(name=name, value="list")


def _string_type(name: str | None = None) -> TypeExpr:
    return AnnotatedType(name=name, value="str")


def _number_type(name: str | None = None) -> TypeExpr:
    return AnnotatedType(name=name, value="float")


def _integer_type(name: str | None = None) -> TypeExpr:
    return AnnotatedType(name=name, value="int")


def _boolean_type(name: str | None = None) -> TypeExpr:
    return AnnotatedType(name=name, value="bool")


def _null_type(name: str | None = None) -> TypeExpr:
    return AnnotatedType(name=name, value="None")


class TypeInterpreter:
    _TYPE_EXPR_MAP = {
        SchemaType.OBJECT: _object_type,
        SchemaType.ARRAY: _array_type,
        SchemaType.STRING: _string_type,
        SchemaType.NUMBER: _number_type,
        SchemaType.INTEGER: _integer_type,
        SchemaType.BOOLEAN: _boolean_type,
        SchemaType.NULL: _null_type,
    }

    def __call__(self, parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
        assert "type" in schema
        type_ = _get_type(schema)
        if type_ not in self._TYPE_EXPR_MAP:
            raise ValueError(f"invalid schema type: {type_}")

        return self._TYPE_EXPR_MAP[type_](expr.name)


def prefixItems(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "prefixItems")


def items(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    if _get_type(schema, SchemaType.ARRAY) != SchemaType.ARRAY:
        raise InterpretError("invalid array type", schema, "items")

    if _get_type(schema) == SchemaType._ANY:
        assert isinstance(expr, UndefinedType)

    items_expr = parser.parse(schema["items"], Context(expr.name, schema, ["items"]))
    if items_expr is None:
        raise InterpretError("failed to interpret schema for array items", schema, "items")
    return AnnotatedType(name=expr.name, value=(_array_type(), [items_expr]))


def contains(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "contains")


def additionalProperties(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "additionalProperties")


def properties(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    if _get_type(schema, SchemaType.OBJECT) != SchemaType.OBJECT:
        raise InterpretError("invalid object type", schema, "properties")

    if _get_type(schema) == SchemaType._ANY:
        assert isinstance(expr, UndefinedType)
    else:
        assert isinstance(expr, ObjectType)

    fields = []
    for k, v in schema["properties"].items():
        prop_expr = parser.parse(v, Context(expr.name, schema, ["properties", k]))
        if prop_expr is None:
            raise InterpretError(
                f"failed to interpret schema for `{k}` property", schema, "properties"
            )
        fields.append(Field(name=k, type=prop_expr))

    return ObjectType(name=expr.name, fields=fields)


def patternProperties(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "additionalProperties")


def dependentSchemas(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "dependentSchemas")


def propertyNames(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "propertyNames")


def if_(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "if")


def then(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "then")


def else_(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "else")


def allOf(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    subschemas = schema["allOf"]
    if not subschemas:
        raise SchemaError("`allOf` must contain one or more subschemas", schema)

    merged: dict = {}
    for i, s in enumerate(subschemas):
        # parse subschemas for traversal
        parser.parse(s, Context(expr.name, schema, ["allOf", i]))

        for k, v in s.items():
            if k not in merged:
                if isinstance(v, Mapping):
                    merged[k] = dict(v)
                elif isinstance(v, list):
                    merged[k] = list(v)
                else:
                    merged[k] = v
            else:
                if isinstance(v, Mapping):
                    merged[k].update(v)
                elif isinstance(v, list):
                    merged[k].extend(v)
                elif k == "type":
                    if merged[k] != v:
                        raise InterpretError("inconsistent subschema types", schema, "allOf")
                else:
                    raise InterpretError(f"cannot merge `{k}` values", schema, "allOf")

    new_expr = parser.parse(merged, context=None)
    if new_expr is None:
        raise InterpretError("cannot interpret merged schema", schema, "allOf")
    object.__setattr__(new_expr, "name", expr.name)

    return new_expr


def anyOf(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    subschemas = schema["anyOf"]
    if not subschemas:
        raise SchemaError("`anyOf` must contain one or more subschemas", schema)

    sub_exprs = []
    for i, s in enumerate(subschemas):
        sub_expr = parser.parse(s, Context(expr.name, schema, ["anyOf", i]))
        if sub_expr is not None:
            sub_exprs.append(sub_expr)

    if not sub_exprs:
        raise InterpretError("no valid exprs found", schema, "anyOf")

    return UnionType(name=expr.name, types=sub_exprs)


def oneOf(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    subschemas = schema["oneOf"]
    if not subschemas:
        raise SchemaError("`oneOf` must contain one or more subschemas", schema)

    sub_exprs = []
    for i, s in enumerate(subschemas):
        sub_expr = parser.parse(s, Context(expr.name, schema, ["oneOf", i]))
        if sub_expr is not None:
            sub_exprs.append(sub_expr)

    if not sub_exprs:
        raise InterpretError("no valid exprs found", schema, "oneOf")

    return UnionType(name=expr.name, types=sub_exprs)


def not_(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "not")


def const(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    # TODO: implement using Literal
    raise NotSupportedError(schema, "const")


def enum(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    if not isinstance(expr, UndefinedType):
        raise InterpretError("invalid enum schema", schema, "enum")

    values = schema["enum"]
    if not isinstance(values, list):
        raise TypeError("enum must be a list")

    # TODO: return EnumType when all values are str

    return AnnotatedType(name=expr.name, value=("typing.Literal", [repr(v) for v in values]))


def multipleOf(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "multipleOf")


def maximum(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "maximum")


def exclusiveMaximum(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "exclusiveMaximum")


def minimum(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "minimum")


def exclusiveMinimum(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "exclusiveMinimum")


def maxLength(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "maxLength")


def minLength(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "minLength")


def pattern(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "pattern")


def maxItems(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "maxItems")


def minItems(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "minItems")


def uniqueItems(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "uniqueItems")


def maxContains(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "maxContains")


def minContains(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "minContains")


def maxProperties(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "maxProperties")


def minProperties(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "minProperties")


def unevaluatedItems(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "unevaluatedItems")


def unevaluatedProperties(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "unevaluatedProperties")


def required(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    if _get_type(schema, SchemaType.OBJECT) != SchemaType.OBJECT:
        raise InterpretError("invalid object type", schema, "required")

    assert isinstance(expr, ObjectType)

    fields = {f.name: f for f in expr.fields}
    for prop in schema["required"]:
        fields[prop] = replace(fields[prop], required=True)

    return ObjectType(name=expr.name, fields=list(fields.values()))


def dependentRequired(parser: Parser, expr: TypeExpr, schema: Schema):
    raise NotSupportedError(schema, "dependentRequired")


def format(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "format")


def contentEncoding(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "contentEncoding")


def contentMediaType(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "contentMediaType")


def contentSchema(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "contentSchema")


def title(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    return expr  # do nothing


def description(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    return expr  # do nothing


def default(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    raise NotSupportedError(schema, "default")


def deprecated(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    return expr  # do nothing


def readOnly(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    return expr  # do nothing


def writeOnly(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    return expr  # do nothing


def examples(parser: Parser, expr: TypeExpr, schema: Schema) -> TypeExpr:
    return expr  # do nothing

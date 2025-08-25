from collections.abc import Mapping
from logging import getLogger
from typing import ClassVar

from jsonschema_codegen import _interpreters, _resolvers
from jsonschema_codegen.exceptions import NotSupportedError
from jsonschema_codegen.exprs import AnnotatedType, TypeExpr, UndefinedType
from jsonschema_codegen.schema import SchemaDict
from jsonschema_codegen.types import Context, Interpreter, NameResolver, Schema

logger = getLogger(__name__)


class SchemaParser:
    def __init__(
        self,
        interpreters: Mapping[str, Interpreter],
        resolver: NameResolver | None = None,
        ignore_unsupported: bool = False,
    ):
        self.interpreters = interpreters
        self.resolver = resolver
        self.ignore_unsupported = ignore_unsupported
        self._refs: dict[str, TypeExpr] = {}

    def parse(self, schema: Schema | bool, context: Context | None = None) -> TypeExpr | None:
        logger.debug(f"{self.__class__.__name__}.parse called: {schema=}, {context=}")

        if isinstance(schema, bool):
            return AnnotatedType("typing.Any")

        if isinstance(schema, SchemaDict) and schema.ref is not None:
            if schema.ref in self._refs:
                return self._refs[schema.ref]

            self._refs[schema.ref] = AnnotatedType(UndefinedType())  # set dummy reference
            expr = self.parse(schema._resolve(), context)
            object.__setattr__(self._refs[schema.ref], "value", expr)  # set actual reference
            return expr

        expr = UndefinedType(
            name=self.resolver.resolve(schema, context) if self.resolver else None
        )

        keys = set(schema.keys())
        for keyword, interpreter in self.interpreters.items():
            if keyword not in keys:
                continue
            keys.remove(keyword)

            try:
                expr = interpreter(self, expr, schema)
            except NotSupportedError as e:
                if self.ignore_unsupported:
                    logger.info(f"ignore unsupported keyword: {e.key}")
                    continue
                raise e

        for key in keys:
            if not key.startswith("$"):
                logger.info(f"undefined keyword: {key}")

        if isinstance(expr, UndefinedType):
            return None

        return expr

    def clear(self):
        self._refs.clear()


class JSONSchemaParser:
    INTERPRETERS: ClassVar[Mapping[str, Interpreter] | None] = None
    APPLY_ORDER: ClassVar[list[str] | None] = None

    def __init__(self, resolver: NameResolver | None = None, ignore_unsupported: bool = False):
        interpreters = dict(self.INTERPRETERS) if self.INTERPRETERS else {}
        if self.APPLY_ORDER:
            priorities = {k: i for i, k in enumerate(self.APPLY_ORDER)}
            interpreters = dict(
                sorted(interpreters.items(), key=lambda x: priorities.get(x[0], len(interpreters)))
            )
        self._parser = SchemaParser(interpreters, resolver, ignore_unsupported)

    def parse(self, schema: Schema | bool, context: Context | None = None) -> TypeExpr | None:
        return self._parser.parse(schema, context)

    def clear(self):
        self._parser.clear()


class Draft202012Parser(JSONSchemaParser):
    INTERPRETERS = {
        # Applicator: https://json-schema.org/draft/2020-12/meta/applicator
        "prefixItems": _interpreters.prefixItems,
        "items": _interpreters.items,
        "contains": _interpreters.contains,
        "additionalProperties": _interpreters.additionalProperties,
        "properties": _interpreters.properties,
        "patternProperties": _interpreters.patternProperties,
        "dependentSchemas": _interpreters.dependentSchemas,
        "propertyNames": _interpreters.propertyNames,
        "if": _interpreters.if_,
        "then": _interpreters.then,
        "else": _interpreters.else_,
        "allOf": _interpreters.allOf,
        "anyOf": _interpreters.anyOf,
        "oneOf": _interpreters.oneOf,
        "not": _interpreters.not_,
        # Validation: https://json-schema.org/draft/2020-12/meta/validation
        "type": _interpreters.TypeInterpreter(),
        "const": _interpreters.const,
        "enum": _interpreters.enum,
        "multipleOf": _interpreters.multipleOf,
        "maximum": _interpreters.maximum,
        "exclusiveMaximum": _interpreters.exclusiveMaximum,
        "minimum": _interpreters.minimum,
        "exclusiveMinimum": _interpreters.exclusiveMinimum,
        "maxLength": _interpreters.maxLength,
        "minLength": _interpreters.minLength,
        "pattern": _interpreters.pattern,
        "maxItems": _interpreters.maxItems,
        "minItems": _interpreters.minItems,
        "uniqueItems": _interpreters.uniqueItems,
        "maxContains": _interpreters.maxContains,
        "minContains": _interpreters.minContains,
        "maxProperties": _interpreters.maxProperties,
        "minProperties": _interpreters.minProperties,
        "required": _interpreters.required,
        "dependentRequired": _interpreters.dependentRequired,
        # Unevaluated: https://json-schema.org/draft/2020-12/meta/unevaluated
        "unevaluatedItems": _interpreters.unevaluatedItems,
        "unevaluatedProperties": _interpreters.unevaluatedProperties,
        # Format Annotation: https://json-schema.org/draft/2020-12/meta/format-annotation
        "format": _interpreters.format,
        # Content: https://json-schema.org/draft/2020-12/meta/content
        "contentEncoding": _interpreters.contentEncoding,
        "contentMediaType": _interpreters.contentMediaType,
        "contentSchema": _interpreters.contentSchema,
        # Meta-Data: https://json-schema.org/draft/2020-12/meta/meta-data
        "title": _interpreters.title,
        "description": _interpreters.description,
        "default": _interpreters.default,
        "deprecated": _interpreters.deprecated,
        "readOnly": _interpreters.readOnly,
        "writeOnly": _interpreters.writeOnly,
        "examples": _interpreters.examples,
    }
    APPLY_ORDER = ["type", "allOf", "anyOf", "oneOf", "properties"]


def create_parser(
    schema: Schema | bool | None = None,
    *,
    resolver: NameResolver | bool | None = None,
    ignore_unsupported: bool = False,
) -> JSONSchemaParser:
    if isinstance(resolver, bool):
        resolver = default_resolver() if resolver else None

    return Draft202012Parser(resolver, ignore_unsupported)


def default_resolver() -> NameResolver:
    return _resolvers.MultiNameResolver(
        resolvers=[
            _resolvers.RefBasedNameResolver(),
            _resolvers.TitleBasedNameResolver(),
            _resolvers.PropertyNameResolver(),
            _resolvers.ArrayItemNameResolver(),
        ]
    )

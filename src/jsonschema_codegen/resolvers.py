from typing import Iterable, Protocol
from urllib.parse import urldefrag

from jsonschema_codegen.schema import SchemaDict
from jsonschema_codegen.types import Context, Schema


class NameResolver(Protocol):
    def resolve(self, schema: Schema, context: Context | None) -> str | None: ...


class NullNameResolver:
    def resolve(self, schema: Schema, context: Context | None) -> str | None:
        return None


class TitleBasedNameResolver:
    def resolve(self, schema: Schema, context: Context | None) -> str | None:
        name = None
        if "title" in schema:
            name = snake_to_camel(schema["title"].replace(" ", "_"))
        return name


class PropertyNameResolver:
    def __init__(self, target_types: Iterable[str] = ("object",)):
        self.target_types = set(target_types)

    def resolve(self, schema: Schema, context: Context | None) -> str | None:
        if context is None or context.schema.get("type") != "object" or context.expr_name is None:
            return None

        if schema.get("type") not in self.target_types:
            return None

        property_name = context.path[-1]
        assert isinstance(property_name, str)
        return context.expr_name + snake_to_camel(property_name)


class ArrayItemNameResolver:
    def __init__(self, target_types: Iterable[str] = ("object",)):
        self.target_types = set(target_types)

    def resolve(self, schema: Schema, context: Context | None) -> str | None:
        if context is None or context.schema.get("type") != "array" or context.expr_name is None:
            return None

        if schema.get("type") not in self.target_types:
            return None

        return context.expr_name + "Item"


class RefBasedNameResolver:
    def resolve(self, schema: Schema, context: Context | None) -> str | None:
        if context is None:
            return None

        context_schema = context.schema
        for index in context.path:
            context_schema = context_schema[index]  # type: ignore[index]

        if not isinstance(context_schema, SchemaDict) or context_schema.ref is None:
            return None

        _uri, fragment = urldefrag(context_schema.ref)
        return fragment.rsplit("/", 1)[-1] if fragment else None


class CombinedNameResolver:
    def __init__(self, resolvers: Iterable[NameResolver]):
        self.resolvers = list(resolvers)

    def resolve(self, schema: Schema, context: Context | None) -> str | None:
        for resolver in self.resolvers:
            name = resolver.resolve(schema, context)
            if name is not None:
                return name

        return None


def default_resolver() -> NameResolver:
    return CombinedNameResolver(
        resolvers=[
            RefBasedNameResolver(),
            TitleBasedNameResolver(),
            PropertyNameResolver(),
            ArrayItemNameResolver(),
        ]
    )


def snake_to_camel(s: str) -> str:
    return "".join(x[0].upper() + x[1:] if x else "" for x in s.split("_"))

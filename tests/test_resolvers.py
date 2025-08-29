from jsonschema_codegen.resolvers import (
    PropertyNameResolver,
    RefBasedNameResolver,
    TitleBasedNameResolver,
)
from jsonschema_codegen.schema import SchemaDict, SchemaVersion
from jsonschema_codegen.types import Context


def test_title_based_name_resolver():
    resolver = TitleBasedNameResolver()

    schema = {
        "title": "test object",
        "type": "object",
    }
    context = None
    name = resolver.resolve(schema, context)
    assert name == "TestObject"

    schema = {
        "type": "object",
    }
    context = None
    name = resolver.resolve(schema, context)
    assert name is None


def test_property_name_resolver():
    resolver = PropertyNameResolver()

    schema: dict = {
        "title": "test object",
        "type": "object",
        "properties": {
            "prop1": {"type": "object"},
            "prop2": {"type": "string"},
            "prop3": {"type": "integer"},
        },
    }
    expected_names = {
        "prop1": "TestObjectProp1",
        "prop2": None,
        "prop3": None,
    }
    for k, v in schema["properties"].items():
        context = Context("TestObject", schema, ["properties", k])
        name = resolver.resolve(v, context)
        assert name == expected_names[k]


def test_ref_based_name_resolver():
    resolver = RefBasedNameResolver()

    schema = SchemaDict(
        {
            "type": "object",
            "properties": {
                "test": {"$ref": "#/$defs/TestObject"},
            },
            "$defs": {
                "TestObject": {
                    "type": "object",
                },
            },
        },
        default_spec=SchemaVersion.DRAFT202012,
    )
    subschema = schema["properties"]["test"]
    context = Context(None, subschema, [])
    name = resolver.resolve(subschema._resolve(), context)
    assert name == "TestObject"

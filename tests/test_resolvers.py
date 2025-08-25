from jsonschema_codegen._resolvers import PropertyNameResolver, TitleBasedNameResolver
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

    schema = {
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

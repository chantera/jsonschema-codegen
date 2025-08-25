from jsonschema_codegen.exprs import AnnotatedType, Field, ObjectType, TypeExpr
from jsonschema_codegen.parsers import create_parser
from jsonschema_codegen.schema import SchemaDict


def test_interpret():
    expected: TypeExpr
    parser = create_parser()

    s = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "integer"},
        },
        "required": ["name"],
    }
    expected = ObjectType(
        fields=[
            Field(name="name", type=AnnotatedType("str"), required=True),
            Field(name="price", type=AnnotatedType("int"), required=False),
        ],
    )
    assert parser.parse(s) == expected

    s = {
        # no explicit type
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "integer"},
        },
        "required": ["name"],
    }
    expected = ObjectType(
        fields=[
            Field(name="name", type=AnnotatedType("str"), required=True),
            Field(name="price", type=AnnotatedType("int"), required=False),
        ],
    )
    assert parser.parse(s) == expected

    s = {
        "type": "array",
        "items": {
            "type": "object",
        },
    }
    expected = AnnotatedType(
        value=("list", [ObjectType()]),
    )
    assert parser.parse(s) == expected

    s = {
        # no explicit type
        "items": {
            "type": "object",
        },
    }
    expected = AnnotatedType(
        value=("list", [ObjectType()]),
    )
    assert parser.parse(s) == expected


def test_interpret_allOf():
    parser = create_parser()

    s = {
        "allOf": [
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["name"],
            },
            {
                "type": "object",
                "properties": {
                    "price": {"type": "integer"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["price"],
            },
        ]
    }
    expected = ObjectType(
        fields=[
            Field(name="name", type=AnnotatedType("str"), required=True),
            Field(name="price", type=AnnotatedType("int"), required=True),
            Field(name="tags", type=AnnotatedType(("list", ["str"])), required=False),
        ],
    )
    ret = parser.parse(SchemaDict(s))
    assert ret == expected


def test_interpret_oneOf():
    parser = create_parser()

    s = {
        "oneOf": [
            {"type": "string"},
            {"type": "integer"},
        ]
    }
    expected = AnnotatedType(
        value=("typing.Union", ["str", "int"]),
    )
    ret = parser.parse(SchemaDict(s))
    assert ret == expected
    assert ret.hint == "typing.Union[str, int]"

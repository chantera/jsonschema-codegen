from jsonschema_codegen.exprs import AnnotatedType, Field, ObjectType, TypeExpr
from jsonschema_codegen.parsers import create_parser


def test_interpret():
    expected: TypeExpr
    parser = create_parser()

    schema = {
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
    assert parser.parse(schema) == expected

    schema = {
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
    assert parser.parse(schema) == expected

    schema = {
        "type": "array",
        "items": {
            "type": "object",
        },
    }
    expected = AnnotatedType(
        value=("list", [ObjectType()]),
    )
    assert parser.parse(schema) == expected

    schema = {
        # no explicit type
        "items": {
            "type": "object",
        },
    }
    expected = AnnotatedType(
        value=("list", [ObjectType()]),
    )
    assert parser.parse(schema) == expected


def test_interpret_allOf():
    parser = create_parser()

    schema = {
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
    ret = parser.parse(schema)
    assert ret == expected


def test_interpret_oneOf():
    parser = create_parser()

    schema = {
        "oneOf": [
            {"type": "string"},
            {"type": "integer"},
        ]
    }
    expected = AnnotatedType(
        value=("typing.Union", ["str", "int"]),
    )
    ret = parser.parse(schema)
    assert ret == expected
    assert ret.hint == "typing.Union[str, int]"

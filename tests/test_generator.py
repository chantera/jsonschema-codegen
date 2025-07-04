from textwrap import dedent

from jsonschema_codegen.exprs import AnnotatedType, Field, ObjectType, UnionType
from jsonschema_codegen.generator import generate


def test_generator():
    expr = ObjectType(
        name="Product",
        fields=[
            Field(name="name", type=AnnotatedType("str")),
            Field(
                name="price",
                type=UnionType([AnnotatedType("int"), AnnotatedType("float")], name="Number"),
            ),
        ],
    )

    expected = dedent("""\
        import typing

        Number = typing.Union[int, float]

        class Product:
            name: str
            price: Number
    """)

    assert generate(expr) == expected

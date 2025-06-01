from textwrap import dedent

from jsonschema_codegen.exprs import AnnotatedType, Field, ObjectType, UnionType
from jsonschema_codegen.renderers import AnnotationRenderer, ObjectRenderer


def test_annotation_renderer():
    renderer = AnnotationRenderer()

    expr = AnnotatedType("str")
    expected = ""
    assert renderer.render(expr) == expected

    expr = AnnotatedType("str", name="ID")
    expected = dedent("""\
        ID = str
    """)
    assert renderer.render(expr) == expected

    expr = UnionType([AnnotatedType("int"), AnnotatedType("float")])
    expected = ""
    assert renderer.render(expr) == expected

    expr = UnionType([AnnotatedType("int"), AnnotatedType("float")], name="Number")
    expected = dedent("""\
        Number = typing.Union[int, float]
    """)
    assert renderer.render(expr) == expected


def test_object_renderer():
    renderer = ObjectRenderer()

    expr = ObjectType(
        name="Product",
        fields=[
            Field(name="name", type=AnnotatedType("str"), required=True),
            Field(name="price", type=AnnotatedType("int"), required=False),
        ],
    )
    expected = dedent("""\
        class Product:
            name: str
            price: int
    """)
    assert renderer.render(expr) == expected

    expr = ObjectType(
        name="Product",
        fields=[
            Field(name="name", type=AnnotatedType("str")),
            Field(name="price", type=UnionType([AnnotatedType("int"), AnnotatedType("float")])),
        ],
    )
    expected = dedent("""\
        class Product:
            name: str
            price: typing.Union[int, float]
    """)
    assert renderer.render(expr) == expected

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
        class Product:
            name: str
            price: Number
    """)
    assert renderer.render(expr) == expected

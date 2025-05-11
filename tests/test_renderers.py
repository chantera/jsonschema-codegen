from textwrap import dedent

from jsonschema_codegen.exprs import AnnotatedType, Field, ObjectType
from jsonschema_codegen.renderers import ObjectRenderer


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

from textwrap import dedent

import pytest

from jsonschema_codegen.compiler import Compiler
from jsonschema_codegen.generator import CodeGenerator
from jsonschema_codegen.parsers import create_parser


@pytest.fixture(scope="module")
def compiler():
    parser = create_parser(resolver=True)
    generator = CodeGenerator()
    compiler = Compiler(parser, generator)
    return compiler


def test_compile(compiler):
    s = {
        "title": "product",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "integer"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["price"],
    }
    expected = dedent("""\
        class Product:
            name: str
            price: int
            tags: list[str]
    """)
    assert compiler.compile(s) == expected

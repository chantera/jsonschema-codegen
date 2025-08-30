from textwrap import dedent

from jsonschema_codegen.compiler import Compiler
from jsonschema_codegen.generator import CodeGenerator
from jsonschema_codegen.parsers import create_parser
from jsonschema_codegen.schema import SchemaDict, SchemaVersion
from jsonschema_codegen.types import Schema


def create_compiler(schema):
    parser = create_parser(
        schema, default_spec=SchemaVersion.DRAFT202012, resolver=True, ignore_unsupported=True
    )
    generator = CodeGenerator()
    compiler = Compiler(parser, generator)
    return compiler


def test_compile():
    schema: Schema = {
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
        from dataclasses import dataclass

        @dataclass
        class Product:
            name: str
            price: int
            tags: list[str]
    """)
    compiler = create_compiler(schema)
    assert compiler.compile(schema) == expected

    schema = SchemaDict(
        {
            "$id": "https://example.com/entry-schema",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "description": "JSON Schema for an fstab entry",
            "title": "fstab entry",
            "type": "object",
            "required": ["storage"],
            "properties": {
                "storage": {
                    "type": "object",
                    "oneOf": [
                        {"$ref": "#/$defs/diskDevice"},
                        {"$ref": "#/$defs/diskUUID"},
                        {"$ref": "#/$defs/nfs"},
                        {"$ref": "#/$defs/tmpfs"},
                    ],
                },
                "fstype": {"enum": ["ext3", "ext4", "btrfs"]},
                "options": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "readonly": {"type": "boolean"},
            },
            "$defs": {
                "diskDevice": {
                    "properties": {
                        "type": {"enum": ["disk"]},
                        "device": {"type": "string", "pattern": "^/dev/[^/]+(/[^/]+)*$"},
                    },
                    "required": ["type", "device"],
                    "additionalProperties": False,
                },
                "diskUUID": {
                    "properties": {
                        "type": {"enum": ["disk"]},
                        "label": {
                            "type": "string",
                            "pattern": "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$",
                        },
                    },
                    "required": ["type", "label"],
                    "additionalProperties": False,
                },
                "nfs": {
                    "properties": {
                        "type": {"enum": ["nfs"]},
                        "remotePath": {"type": "string", "pattern": "^(/[^/]+)+$"},
                        "server": {
                            "type": "string",
                            "oneOf": [
                                {"type": "string", "format": "hostname"},
                                {"type": "string", "format": "ipv4"},
                                {"type": "string", "format": "ipv6"},
                            ],
                        },
                    },
                    "required": ["type", "server", "remotePath"],
                    "additionalProperties": False,
                },
                "tmpfs": {
                    "properties": {
                        "type": {"enum": ["tmpfs"]},
                        "sizeInMB": {"type": "integer", "minimum": 16, "maximum": 512},
                    },
                    "required": ["type", "sizeInMB"],
                    "additionalProperties": False,
                },
            },
        }
    )
    expected = dedent("""\
        from dataclasses import dataclass
        import typing

        @dataclass
        class diskDevice:
            type: typing.Literal['disk']
            device: str

        @dataclass
        class diskUUID:
            type: typing.Literal['disk']
            label: str

        @dataclass
        class nfs:
            type: typing.Literal['nfs']
            remotePath: str
            server: typing.Union[str, str, str]

        @dataclass
        class tmpfs:
            type: typing.Literal['tmpfs']
            sizeInMB: int

        FstabEntryStorage = typing.Union[diskDevice, diskUUID, nfs, tmpfs]

        @dataclass
        class FstabEntry:
            storage: FstabEntryStorage
            fstype: typing.Literal['ext3', 'ext4', 'btrfs']
            options: list[str]
            readonly: bool
    """)
    compiler = create_compiler(schema)
    assert compiler.compile(schema) == expected

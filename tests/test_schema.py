from jsonschema_codegen.schema import create_resolver

import pytest
import referencing.exceptions


def test_create_resolver():
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example:a-202012-schema",
        "$defs": {
            "nonNegativeInteger": {
                "$anchor": "nonNegativeInteger",
                "type": "integer",
                "minimum": 0,
            },
        },
    }
    resolver = create_resolver(schema)

    resolved = resolver.lookup("urn:example:a-202012-schema#nonNegativeInteger")
    assert resolved.contents == {
        "$anchor": "nonNegativeInteger",
        "type": "integer",
        "minimum": 0,
    }

    schema = {
        "$id": "urn:example:a-202012-schema",
        "$defs": {
            "nonNegativeInteger": {
                "$anchor": "nonNegativeInteger",
                "type": "integer",
                "minimum": 0,
            },
        },
    }
    with pytest.raises(referencing.exceptions.CannotDetermineSpecification):
        resolver = create_resolver(schema)
    resolver = create_resolver(schema, default_spec="draft202012")

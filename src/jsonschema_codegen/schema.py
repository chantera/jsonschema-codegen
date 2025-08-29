import json
from collections.abc import Mapping
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin
from urllib.request import urlopen

import referencing
import referencing.jsonschema
import yaml


def create_resolver(
    schema: dict,
    default_spec: referencing.Specification | str | None = None,
    base_uri: str | None = None,
    retrieve: Callable[[str], dict] | None | bool = None,
):
    if retrieve:
        initial_registry = referencing.Registry(
            retrieve=_create_retriever(  # type: ignore[call-arg]
                _default_retrieve if retrieve is True else retrieve, default_spec
            )
        )
    else:
        initial_registry = referencing.Registry()

    resource = _create_resource(schema, default_spec)
    uri = base_uri if base_uri else resource.id() or ""

    registry = initial_registry.with_resource(uri, resource)
    return registry.resolver(uri)


def _resolve_dict(data, resolver):
    if "$ref" not in data:
        return data, resolver

    if resolver is None:
        raise ValueError("Resolver must be provided")

    resolved = resolver.lookup(data["$ref"])
    if not isinstance(resolved.contents, dict):
        raise TypeError("Resolved content is expected to be a dict, got {type(resolved.content)}")

    return _resolve_dict(resolved.contents, resolved.resolver)


class SchemaDict(Mapping):
    def __init__(self, data: dict, /, resolver=None, **kwargs):
        if not isinstance(data, dict):
            raise TypeError(f"data must be a dict, got {type(data)}")
        if resolver is None:
            resolver = create_resolver(data, **kwargs)

        self.data = data
        self._resolved: dict | None = None
        self._resolver = resolver

    def _resolve(self) -> dict:
        if self._resolved is None:
            content, resolver = _resolve_dict(self.data, self._resolver)

            self._resolved = {}
            for k, v in content.items():
                if isinstance(v, dict):
                    v = SchemaDict(v, resolver=resolver)
                elif isinstance(v, list):
                    v = _schema_list(v, resolver=resolver)
                self._resolved[k] = v

        return self._resolved

    def __getitem__(self, key):
        resolved = self._resolve()
        if key in resolved:
            return resolved[key]
        raise KeyError(key)

    def __len__(self):
        return len(self._resolve())

    def __iter__(self):
        return iter(self._resolve())

    def __contains__(self, key):
        return key in self._resolve()

    def __repr__(self):
        content = repr(self._resolved if self._resolved is not None else self.data)
        return f"SchemaDict({content})"

    def get(self, key, default=None):
        return self._resolve().get(key, default)

    @cached_property
    def ref(self) -> str | None:
        ref = self.data.get("$ref")
        if ref is not None:
            ref = urljoin(self._resolver._base_uri, ref)
        return ref

    @classmethod
    def from_file(cls, path: str) -> "SchemaDict":
        p = Path(path).absolute()
        with open(p) as f:
            schema = yaml.safe_load(f) if path.endswith((".yaml", ".yml")) else json.load(f)
        return cls(schema, base_uri=p.as_uri())


def _schema_list(data: list, resolver):
    ret = []
    for v in data:
        if isinstance(v, dict):
            v = SchemaDict(v, resolver=resolver)
        elif isinstance(v, list):
            v = _schema_list(v, resolver=resolver)
        ret.append(v)
    return ret


class SchemaVersion(StrEnum):
    DRAFT202012 = "https://json-schema.org/draft/2020-12/schema"
    DRAFT201909 = "https://json-schema.org/draft/2019-09/schema"
    DRAFT07 = "http://json-schema.org/draft-07/schema#"
    DRAFT06 = "http://json-schema.org/draft-06/schema#"
    DRAFT04 = "http://json-schema.org/draft-04/schema#"
    DRAFT03 = "http://json-schema.org/draft-03/schema#"


_SPECS = {
    SchemaVersion.DRAFT202012: referencing.jsonschema.DRAFT202012,
    SchemaVersion.DRAFT201909: referencing.jsonschema.DRAFT201909,
    SchemaVersion.DRAFT07: referencing.jsonschema.DRAFT7,
    SchemaVersion.DRAFT06: referencing.jsonschema.DRAFT6,
    SchemaVersion.DRAFT04: referencing.jsonschema.DRAFT4,
    SchemaVersion.DRAFT03: referencing.jsonschema.DRAFT3,
}


def _create_resource(
    contents: dict, default_spec: referencing.Specification | str | None = None
) -> referencing.Resource:
    kwargs = {}
    if default_spec is not None:
        if isinstance(default_spec, str):
            if default_spec not in _SPECS:
                raise ValueError(f"Unknown specification: {default_spec}")
            default_spec = _SPECS[default_spec]  # type: ignore[index]
        kwargs["default_specification"] = default_spec

    return referencing.Resource.from_contents(contents, **kwargs)


def _create_retriever(
    f: Callable[[str], dict], default_spec: referencing.Specification | str | None = None
) -> Callable[[str], referencing.Resource]:
    def retrieve(uri: str) -> referencing.Resource:
        contents = f(uri)
        return _create_resource(contents, default_spec)

    return retrieve


def _default_retrieve(uri: str) -> dict:
    with urlopen(uri) as f:
        if uri.endswith((".yaml", ".yml")):
            return yaml.safe_load(f)
        else:
            return json.load(f)

from collections.abc import Mapping
from functools import cached_property
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

import referencing
import referencing.jsonschema
import yaml


def _retrieve(uri):
    with urlopen(uri) as response:
        return referencing.Resource.from_contents(
            yaml.safe_load(response),
            default_specification=referencing.jsonschema.DRAFT202012,
        )


_DEFAULT_REGISTRY = referencing.Registry(retrieve=_retrieve)  # type: ignore


def _create_resolver(schema: dict, base_uri: str = ""):
    resource = referencing.jsonschema.DRAFT202012.create_resource(schema)
    registry = _DEFAULT_REGISTRY.with_resource(base_uri, resource)
    return registry.resolver(base_uri)


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
        if resolver is None and kwargs:
            resolver = _create_resolver(data, **kwargs)
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
        return repr(self._resolved if self._resolved is not None else self.data)

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
        with open(p) as file:
            schema = yaml.safe_load(file)
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

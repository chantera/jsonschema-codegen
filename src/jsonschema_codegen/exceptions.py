from jsonschema_codegen.types import Schema


class SchemaError(Exception):
    def __init__(self, message: str, schema: Schema | bool, key: str | None = None):
        self.message = message
        self.schema = schema
        self.key = key

    def __str__(self) -> str:
        s = f"{self.message}: schema={self.schema}"
        if self.key is not None:
            s += f", key={self.key!r}"
        return s

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


class InterpretError(Exception):
    def __init__(self, message: str, schema: Schema, key: str):
        self.message = message
        self.schema = schema
        self.key = key

    def __str__(self) -> str:
        return f"{self.message}: schema={self.schema}, key={self.key!r}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


class NotSupportedError(Exception):
    def __init__(self, schema: Schema, key: str):
        self._message = f"`{key}` is not supported"
        self.schema = schema
        self.key = key

    def __str__(self) -> str:
        return f"{self._message}: schema={self.schema}, key={self.key!r}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._message!r})"

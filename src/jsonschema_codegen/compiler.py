from jsonschema_codegen.generator import CodeGenerator
from jsonschema_codegen.parsers import JSONSchemaParser
from jsonschema_codegen.types import Schema

SchemaLike = Schema | bool


class Compiler:
    def __init__(self, parser: JSONSchemaParser, generator: CodeGenerator):
        self.parser = parser
        self.generator = generator
        self._imports: set[str] = set()

    def compile(self, schema: SchemaLike | list[SchemaLike]) -> str:
        self.parser.clear()
        self.generator.clear()

        if not isinstance(schema, list):
            schema = [schema]

        for instance in schema:
            expr = self.parser.parse(instance)
            if expr is None:
                continue
            self.generator.add(expr)

        output = self.generator.generate()
        return output

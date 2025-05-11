from pathlib import Path
from typing import ClassVar

from jinja2 import Environment, FileSystemLoader

from jsonschema_codegen.exprs import ObjectType, TypeExpr

TEMPLATE_DIR = Path(__file__).parent / "templates"


class Renderer:
    TEMPLATE_NAME: ClassVar[str] = ""

    def __init__(self, template_dir: str | Path | None = None):
        if not self.TEMPLATE_NAME:
            raise ValueError(f"{self.__class__.__name__}.TEMPLATE_NAME must be set")

        env = Environment(
            loader=FileSystemLoader(template_dir or TEMPLATE_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = env.get_template(self.TEMPLATE_NAME)

    def render(self, expr: TypeExpr) -> str:
        raise NotImplementedError


class ObjectRenderer(Renderer):
    TEMPLATE_NAME = "object.jinja2"

    def render(self, expr: TypeExpr) -> str:
        if not isinstance(expr, ObjectType):
            raise TypeError(f"Expected `ObjectType`, got `{type(expr).__name__}`")

        return self.template.render(
            name=expr.identifier,
            fields=expr.fields,
        )

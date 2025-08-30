from functools import lru_cache
from pathlib import Path
from typing import ClassVar

from jinja2 import Environment, FileSystemLoader, Template

from jsonschema_codegen.exprs import AnnotatedType, ObjectType, TypeExpr

TEMPLATE_DIR = Path(__file__).parent / "templates"


@lru_cache
def _get_env(template_dir: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _get_template(name: str, template_dir: str | Path | None = None) -> Template:
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    elif isinstance(template_dir, str):
        template_dir = Path(template_dir)

    env = _get_env(str(template_dir.resolve()))
    return env.get_template(name)


def get_header(template_dir: str | Path | None = None) -> Template:
    return _get_template("header.jinja2", template_dir)


class Renderer:
    TEMPLATE_NAME: ClassVar[str] = ""

    def __init__(self, template_dir: str | Path | None = None):
        if not self.TEMPLATE_NAME:
            raise ValueError(f"{self.__class__.__name__}.TEMPLATE_NAME must be set")

        self.template = _get_template(self.TEMPLATE_NAME, template_dir)

    def render(self, expr: TypeExpr) -> str:
        raise NotImplementedError


class AnnotationRenderer(Renderer):
    TEMPLATE_NAME = "annotation.jinja2"

    def render(self, expr: TypeExpr) -> str:
        if not isinstance(expr, AnnotatedType):
            raise TypeError(f"Expected `AnnotatedType`, got `{type(expr).__name__}`")

        return self.template.render(
            name=expr.name,
            annotation=expr.annotation,
        )


class ObjectRenderer(Renderer):
    TEMPLATE_NAME = "object.jinja2"

    def render(self, expr: TypeExpr) -> str:
        if not isinstance(expr, ObjectType):
            raise TypeError(f"Expected `ObjectType`, got `{type(expr).__name__}`")

        return self.template.render(
            name=expr.identifier,
            fields=expr.fields,
        )

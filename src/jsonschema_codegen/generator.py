from pathlib import Path
from typing import Iterator

from jsonschema_codegen.exprs import AnnotatedType, Annotation, ObjectType, TypeExpr, UnionType
from jsonschema_codegen.renderers import AnnotationRenderer, ObjectRenderer, get_header


class CodeGenerator:
    def __init__(self, template_dir: str | Path | None = None):
        self._exprs: dict[str, TypeExpr] = {}
        self._imports: set[str] = set()
        self.header = get_header(template_dir)
        self.renderers = {
            AnnotatedType: AnnotationRenderer(template_dir),
            UnionType: AnnotationRenderer(template_dir),
            ObjectType: ObjectRenderer(template_dir),
        }

    def clear(self):
        self._exprs = {}
        self._imports = set()

    def add(self, expr: TypeExpr):
        subtypes = None
        if isinstance(expr, AnnotatedType):
            imports: list[str] = []
            subtypes = list(_iter_annotated_exprs(expr.value, imports))
            self._imports.update(imports)
        elif isinstance(expr, ObjectType):
            if not expr.name:
                raise ValueError(
                    f"ObjectType must have a name: fields={[f.name for f in expr.fields]}"
                )
            subtypes = [field.type for field in expr.fields]

        # add subtypes first for resolving dependencies
        if subtypes:
            for subtype in subtypes:
                self.add(subtype)

        if expr.name:
            # TODO: check duplicate
            assert expr.name not in self._exprs
            self._exprs[expr.name] = expr

    def generate(self) -> str:
        if not self._exprs:
            return ""

        buf = []

        imports = []
        for module_str in self._imports:
            imports.append(f"import {module_str}")

        buf.append(self.header.render(imports=imports))

        for expr in self._exprs.values():
            buf.append(self._render(expr))

        return "\n".join(s for s in buf if s)

    def _render(self, expr: TypeExpr) -> str:
        renderer = self.renderers.get(type(expr))
        if not renderer:
            raise TypeError(f"Unsupported type: {type(expr).__name__}")
        return renderer.render(expr)


def generate(expr: TypeExpr, template_dir: str | Path | None = None) -> str:
    generator = CodeGenerator(template_dir)
    generator.add(expr)
    return generator.generate()


def _iter_annotated_exprs(value: Annotation, imports: list[str]) -> Iterator[TypeExpr]:
    if isinstance(value, TypeExpr):
        yield value
    elif isinstance(value, tuple):
        yield from _iter_annotated_exprs(value[0], imports)
        for v in value[1]:
            yield from _iter_annotated_exprs(v, imports)
    else:  # str
        if "." in value:
            imports.append(value.rsplit(".", maxsplit=1)[0])

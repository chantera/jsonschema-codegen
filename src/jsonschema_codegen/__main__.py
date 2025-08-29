import argparse
import json
import os
import sys
from contextlib import nullcontext

from jsonschema_codegen.compiler import Compiler
from jsonschema_codegen.generator import CodeGenerator
from jsonschema_codegen.parsers import create_parser
from jsonschema_codegen.schema import SchemaDict, SchemaVersion

DEFAULT_SPEC = SchemaVersion.DRAFT202012


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("input", nargs="?")
    argparser.add_argument("--output", "-o")
    args = argparser.parse_args()

    parser = create_parser(default_spec=DEFAULT_SPEC, resolver=True, ignore_unsupported=True)
    generator = CodeGenerator()
    compiler = Compiler(parser, generator)

    if args.input:
        schema = SchemaDict.from_file(args.input)
    else:
        try:
            if sys.stdin.isatty():
                eof_hint = "Press Ctrl+Z and then Enter" if os.name == "nt" else "Press Ctrl+D"
                sys.stderr.write(f"Write JSON schema ({eof_hint} to finish):\n> ")
                sys.stderr.flush()

            schema = SchemaDict(json.loads(sys.stdin.read()), default_spec=DEFAULT_SPEC)
        except json.JSONDecodeError as e:
            print(f"\n{type(e).__module__}.{type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(1)

    output = compiler.compile(schema)

    with open(args.output, "w") if args.output else nullcontext(sys.stdout) as f:
        f.write(output)


if __name__ == "__main__":
    main()

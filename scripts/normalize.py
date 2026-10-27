"""Normalize Python source for scripts/compare.sh.

Reads source on stdin and prints a canonical form: comments and formatting
vanish (the code is parsed and re-printed), docstrings are dropped, and the
top-level statements are sorted so their order does not matter. Two files
that differ only in those ways print the same text.
"""

import ast
import sys


def drop_docstrings(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            )
            and isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]


def main() -> None:
    source = sys.stdin.read()
    try:
        tree = ast.parse(source)
    except SyntaxError as err:
        print(f"<syntax error on line {err.lineno}: {err.msg}>")
        return
    drop_docstrings(tree)
    blocks = sorted(ast.unparse(stmt) for stmt in tree.body)
    print("\n".join(blocks))


main()

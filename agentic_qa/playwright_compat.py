"""Conservative, source-preserving compatibility fixes for generated Python Playwright tests.

Only a literal substring predicate in a to_have_text(lambda ...) call is rewritten.
No expected string, locator, test case, or control flow is changed. Unknown patterns
remain untouched and must follow normal test failure/repair review.
"""
import ast


def _position(lines: list[str], line: int, byte_column: int) -> int:
    prefix = lines[line - 1].encode("utf-8")[:byte_column]
    return sum(len(value) for value in lines[:line - 1]) + len(prefix.decode("utf-8"))



def _url_assertion_fix(node: ast.Call, source: str) -> str | None:
    """Only rewrite exact URL lambda equality / literal-prefix membership.

    Preserve the expected URL string. Never relax arbitrary URL assertions.
    """
    if node.keywords or len(node.args) != 1:
        return None
    method = node.func
    if not (isinstance(method, ast.Attribute) and method.attr == "to_have_url"):
        return None
    receiver = method.value
    if not (isinstance(receiver, ast.Call)
            and isinstance(receiver.func, ast.Name)
            and receiver.func.id == "expect"):
        return None
    predicate = node.args[0]
    if not isinstance(predicate, ast.Lambda):
        return None
    params = predicate.args
    if (len(params.args) != 1 or params.posonlyargs or params.kwonlyargs
            or params.defaults or params.kw_defaults or params.vararg or params.kwarg):
        return None
    arg = params.args[0].arg
    body = predicate.body
    # Equality against a literal absolute URL is exactly expressible by the API.
    if (isinstance(body, ast.Compare) and len(body.ops) == 1
            and isinstance(body.ops[0], ast.Eq)
            and len(body.comparators) == 1):
        left, right = body.left, body.comparators[0]
        for literal, variable in ((left, right), (right, left)):
            if (isinstance(literal, ast.Constant)
                    and isinstance(literal.value, str)
                    and isinstance(variable, ast.Name) and variable.id == arg):
                original_receiver = ast.get_source_segment(source, receiver)
                return original_receiver + ".to_have_url(" + repr(literal.value) + ")"
    return None


def normalize_playwright_assertions(source: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    replacements: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            url_replacement = _url_assertion_fix(node, source)
            if url_replacement is not None:
                start = _position(lines, node.lineno, node.col_offset)
                end = _position(lines, node.end_lineno, node.end_col_offset)
                replacements.append((start, end, url_replacement))
                continue
        if not isinstance(node, ast.Call) or node.keywords or len(node.args) != 1:
            continue
        method = node.func
        if not (isinstance(method, ast.Attribute) and method.attr == "to_have_text"):
            continue
        receiver = method.value
        if not (isinstance(receiver, ast.Call)
                and isinstance(receiver.func, ast.Name)
                and receiver.func.id == "expect"):
            continue
        predicate = node.args[0]
        if not isinstance(predicate, ast.Lambda):
            continue
        params = predicate.args
        if (len(params.args) != 1 or params.posonlyargs or params.kwonlyargs
                or params.defaults or params.kw_defaults or params.vararg or params.kwarg):
            continue
        body = predicate.body
        if not (isinstance(body, ast.Compare) and len(body.ops) == 1
                and isinstance(body.ops[0], ast.In) and len(body.comparators) == 1
                and isinstance(body.left, ast.Constant)
                and isinstance(body.left.value, str)
                and isinstance(body.comparators[0], ast.Name)
                and body.comparators[0].id == params.args[0].arg):
            continue
        original_receiver = ast.get_source_segment(source, receiver)
        if not original_receiver:
            continue
        replacement = original_receiver + ".to_contain_text(" + repr(body.left.value) + ")"
        start = _position(lines, node.lineno, node.col_offset)
        end = _position(lines, node.end_lineno, node.end_col_offset)
        replacements.append((start, end, replacement))
    updated = source
    for start, end, replacement in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    ast.parse(updated)
    return updated

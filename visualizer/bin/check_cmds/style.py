import ast
import sys
from pathlib import Path

IGNORE_FILES = {
    "__init__.py",
    "conftest.py",
    "formatters.py",
}

GET_OR_NONE_ALLOWED_FILES = {
    "db.py",
}

IGNORE_DIRS = {
    "tests",
    "bin",
    "input_objects",
    "base",
}

PACKAGE_ROOT = Path(".")


def _is_exception_class(node: ast.ClassDef) -> bool:
    """Check if a class is an exception (inherits from Exception/Error)."""
    for base in node.bases:
        if isinstance(base, ast.Name) and (
            base.id.endswith("Error")
            or base.id.endswith("Exception")
            or base.id == "Exception"
        ):
            return True
    return False


def count_classes(file_path: Path) -> list[str]:
    """Check for multiple top-level class definitions in one file."""
    with open(file_path) as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    # Only count non-exception top-level classes
    classes = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not _is_exception_class(node)
    ]

    if len(classes) > 1:
        return [f"{file_path}: multiple classes ({', '.join(classes)})"]
    return []


def check_manual_dict_return(file_path: Path) -> list[str]:
    """Check for return statements with dict literals in boundary layer."""
    with open(file_path) as f:
        content = f.read()
        tree = ast.parse(content, filename=str(file_path))

    violations = []
    lines = content.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value:
            if isinstance(node.value, ast.Dict):
                line = lines[node.lineno - 1].strip()
                violations.append(
                    f"{file_path}:{node.lineno}: manual dict return: {line}"
                )

    return violations


def check_context_classes(file_path: Path) -> list[str]:
    """Check that context.py files only have functions, not classes."""
    if file_path.name != "context.py":
        return []

    with open(file_path) as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    if classes:
        return [
            f"{file_path}: context file should not have classes ({', '.join(classes)})"
        ]
    return []


COMPOUND_TYPES = (
    ast.If,
    ast.For,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.AsyncFor,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
)


def _is_compound(node: ast.stmt) -> bool:
    """Check if a statement is compound or spans multiple lines."""
    if isinstance(node, COMPOUND_TYPES):
        return True

    end = node.end_lineno or node.lineno
    return end > node.lineno


def _is_docstring(node: ast.stmt) -> bool:
    """Check if a node is a docstring expression."""
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _iter_bodies(node: ast.AST):
    """Yield all body lists from a compound statement."""
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        yield node.body
        if node.orelse:
            yield node.orelse
    elif isinstance(node, ast.If):
        yield node.body
        if node.orelse:
            yield node.orelse
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        yield node.body
    elif isinstance(node, ast.Try):
        yield node.body
        for handler in node.handlers:
            yield handler.body
        if node.orelse:
            yield node.orelse
        if node.finalbody:
            yield node.finalbody


def check_function_spacing(file_path: Path) -> list[str]:
    """Check spacing inside function bodies.

    Rules:
    - No blank lines between consecutive one-liner statements
    - Blank line before and after multi-line compound statements (if, for, try, etc.)
    - No blank line between block header and first statement
    """
    with open(file_path) as f:
        content = f.read()
        tree = ast.parse(content, filename=str(file_path))

    lines = content.splitlines()
    violations = []

    for node in ast.walk(tree):
        # Preamble check for all compound statement bodies
        for body in _iter_bodies(node):
            if not body:
                continue

            first_stmt = body[0]
            line_before_idx = first_stmt.lineno - 2

            if line_before_idx >= 0 and lines[line_before_idx].strip() == "":
                violations.append(
                    f"{file_path}:{first_stmt.lineno}: unnecessary blank line after block header"
                )

        # Function-specific checks
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        body = node.body
        if not body:
            continue

        has_docstring = _is_docstring(body[0])
        first_real_idx = 1 if has_docstring else 0

        if first_real_idx < len(body):
            first_stmt = body[first_real_idx]
            line_before_idx = first_stmt.lineno - 2

            if line_before_idx >= 0 and lines[line_before_idx].strip() == "":
                violations.append(
                    f"{file_path}:{first_stmt.lineno}: unnecessary blank line after block header"
                )

        if len(body) < 2:
            continue

        for i in range(len(body) - 1):
            if i == 0 and has_docstring:
                continue

            curr = body[i]
            nxt = body[i + 1]
            curr_end = curr.end_lineno or curr.lineno
            nxt_start = nxt.lineno
            blank_lines = nxt_start - curr_end - 1

            if not _is_compound(curr) and not _is_compound(nxt):
                if blank_lines > 0:
                    violations.append(
                        f"{file_path}:{nxt_start}: unnecessary blank line between one-liners"
                    )
            else:
                if blank_lines == 0:
                    violations.append(
                        f"{file_path}:{nxt_start}: missing blank line around compound statement"
                    )

    return violations


def check_get_or_none(file_path: Path) -> list[str]:
    """Check for usage of get_or_none (use find_by instead)."""
    if file_path.name in GET_OR_NONE_ALLOWED_FILES:
        return []

    violations = []

    with open(file_path) as f:
        for lineno, line in enumerate(f, 1):
            if "get_or_none" in line:
                violations.append(
                    f"{file_path}:{lineno}: use find_by instead of get_or_none"
                )

    return violations


def should_check(file_path: Path) -> bool:
    """Determine if file should be checked."""
    if file_path.name in IGNORE_FILES:
        return False
    for ignore_dir in IGNORE_DIRS:
        if ignore_dir in file_path.parts:
            return False
    return True


def main():
    all_violations = []

    # Check boundary layer for manual dict returns
    boundary_path = PACKAGE_ROOT / "boundary"
    if boundary_path.exists():
        for py_file in boundary_path.rglob("*.py"):
            if should_check(py_file):
                all_violations.extend(check_manual_dict_return(py_file))
                all_violations.extend(count_classes(py_file))
                all_violations.extend(check_function_spacing(py_file))
                all_violations.extend(check_get_or_none(py_file))

    # Check lib layer
    lib_path = PACKAGE_ROOT / "lib"
    if lib_path.exists():
        for py_file in lib_path.rglob("*.py"):
            if should_check(py_file):
                all_violations.extend(count_classes(py_file))
                all_violations.extend(check_context_classes(py_file))
                all_violations.extend(check_function_spacing(py_file))
                all_violations.extend(check_get_or_none(py_file))

    # Check infra layer
    infra_path = PACKAGE_ROOT / "infra"
    if infra_path.exists():
        for py_file in infra_path.rglob("*.py"):
            if should_check(py_file):
                all_violations.extend(count_classes(py_file))
                all_violations.extend(check_function_spacing(py_file))
                all_violations.extend(check_get_or_none(py_file))

    if all_violations:
        print("Style violations found:\n")
        for v in sorted(all_violations):
            print(f"  {v}")
        print("\nRules:")
        print("  - One class per file (except __init__.py)")
        print("  - No manual dict returns in boundary layer (use serializers)")
        print("  - Context files should only have functions, not classes")
        print("  - No blank lines between one-liners; blank line around compound statements")
        print("  - No blank line between block header and first statement")
        print("  - Use find_by instead of get_or_none")
        sys.exit(1)
    else:
        print("Style check passed")


if __name__ == "__main__":
    main()

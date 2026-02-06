import ast
import sys
from pathlib import Path

RULES = {
    "infra": {
        "allowed": [],
        "description": "infra should not depend on internal modules",
    },
    "lib": {
        "allowed": ["infra"],
        "description": "lib should only depend on infra",
    },
    "boundary": {
        "allowed": ["lib"],
        "description": "boundary can only depend on lib (not infra)",
    },
}

INTERNAL_MODULES = {"infra", "lib", "boundary"}


def get_imports(file_path: Path) -> list[tuple[str, str]]:
    """Returns list of (internal_top_level, full_import_path) tuples."""
    with open(file_path) as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] in INTERNAL_MODULES:
                    imports.append((parts[0], alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                parts = node.module.split(".")
                if parts[0] in INTERNAL_MODULES:
                    imports.append((parts[0], node.module))
    return imports


def check_file(file_path: Path, layer: str) -> list[str]:
    violations = []
    allowed = RULES[layer]["allowed"]

    for top_level, full_path in get_imports(file_path):
        if (
            top_level in INTERNAL_MODULES
            and top_level != layer
            and top_level not in allowed
        ):
            violations.append(
                f"{file_path}: imports '{full_path}' ({top_level} not allowed)"
            )

    return violations


def print_dependency_diagram():
    """Print ASCII diagram of allowed dependencies."""
    diagram = """
  ┌────────────┐       ┌────────────┐       ┌────────────┐
  │  boundary  │ ───▶  │    lib     │ ───▶  │   infra    │
  └────────────┘       └────────────┘       └────────────┘
    HTTP layer          Business logic       Infrastructure
"""
    print(diagram)


def main():
    root = Path(".")
    all_violations = []

    for layer in RULES:
        layer_path = root / layer
        if not layer_path.exists():
            continue

        for py_file in layer_path.rglob("*.py"):
            violations = check_file(py_file, layer)
            all_violations.extend(violations)

    print_dependency_diagram()

    if all_violations:
        print("Violations found:\n")
        for v in all_violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("Architecture check passed")


if __name__ == "__main__":
    main()

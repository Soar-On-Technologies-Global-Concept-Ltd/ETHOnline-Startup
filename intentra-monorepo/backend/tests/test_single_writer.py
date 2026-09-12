"""Only the state machine assigns transactions.state (rule R1, schematics §3.6)."""
import ast
import pathlib

APP = pathlib.Path(__file__).resolve().parents[1] / "app"
ALLOWED = {APP / "domains/transactions/machine.py"}


def _assignments_to_state(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Attribute) and target.attr == "state":
                found.append(f"{path.relative_to(APP.parent)}:{node.lineno}")
            if isinstance(target, ast.Tuple):
                for element in target.elts:
                    if isinstance(element, ast.Attribute) and element.attr == "state":
                        found.append(f"{path.relative_to(APP.parent)}:{node.lineno}")
    return found


def test_no_module_outside_the_state_machine_writes_state():
    offenders = [hit for path in APP.rglob("*.py") if path not in ALLOWED for hit in _assignments_to_state(path)]
    assert offenders == [], f"only services/state/machine.py may assign .state — found {offenders}"


def test_the_state_machine_does_write_it():
    assert _assignments_to_state(APP / "domains/transactions/machine.py")

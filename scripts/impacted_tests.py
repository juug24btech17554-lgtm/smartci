"""Print the test files affected by the files changed in a git diff.

Usage: python scripts/impacted_tests.py [BASE_COMMIT]
Prints the test files to run. Prints nothing if no test is affected.
"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# If one of these changes, everything must be re-run
RUN_ALL_FILES = {"requirements.txt", "pytest.ini", ".github/workflows/ci.yml"}


def changed_files(base):
    out = subprocess.run(["git", "diff", "--name-only", base, "HEAD"],
                         capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        return None
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def direct_deps(rel):
    """Files in src/ that this file imports directly."""
    tree = ast.parse((ROOT / rel).read_text())
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src."):
            deps.add(node.module.replace(".", "/") + ".py")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src."):
                    deps.add(alias.name.replace(".", "/") + ".py")
    return deps


def all_deps(rel, seen=None):
    """Direct and indirect dependencies (cart -> pricing, test_cart -> cart -> pricing)."""
    seen = set() if seen is None else seen
    for dep in direct_deps(rel):
        if dep not in seen and (ROOT / dep).exists():
            seen.add(dep)
            all_deps(dep, seen)
    return seen


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    tests = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").glob("test_*.py"))
    changed = changed_files(base)

    if changed is None:
        print("git diff failed -> run all tests", file=sys.stderr)
        print(" ".join(tests))
        return
    print("Changed files:", changed, file=sys.stderr)

    if any(f in RUN_ALL_FILES for f in changed):
        print("Config or dependency file changed -> run all tests", file=sys.stderr)
        print(" ".join(tests))
        return

    impacted = []
    for t in tests:
        if t in changed or all_deps(t) & set(changed):
            impacted.append(t)
    print(" ".join(impacted))


if __name__ == "__main__":
    main()
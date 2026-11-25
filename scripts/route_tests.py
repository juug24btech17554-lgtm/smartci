"""Dynamic test-subset routing.

Usage: python scripts/route_tests.py [BASE_COMMIT]
Prints JSON for a GitHub Actions matrix:
{"include": [{"name": ..., "files": ..., "reason": ...}, ...]}
Each entry is one test subset (one test file) that must run, with the reason why.
"""
import json
import sys

from impacted_tests import ROOT, RUN_ALL_FILES, changed_files, all_deps


def route(base):
    tests = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").glob("test_*.py"))
    changed = changed_files(base)

    run_all_reason = None
    if changed is None:
        run_all_reason = "git diff failed, run everything"
    elif any(f in RUN_ALL_FILES for f in changed):
        run_all_reason = "config or dependency file changed, run everything"

    routes = []
    for t in tests:
        name = t.split("/")[-1].replace(".py", "")
        if run_all_reason:
            reason = run_all_reason
        elif t in changed:
            reason = "test file changed"
        else:
            hit = sorted(all_deps(t) & set(changed))
            reason = ("depends on " + ", ".join(hit)) if hit else None
        if reason:
            routes.append({"name": name, "files": t, "reason": reason})
    return {"include": routes}


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    print(json.dumps(route(base)))
    
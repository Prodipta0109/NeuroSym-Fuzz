#!/usr/bin/env python3
"""
Proof-of-bug script for tests/test_anbncn.py's target code
(examples/anbncn/anbncn_data.py) in ML-KULeuven/deepstochlog.

Run with:
    python3 prove_anbncn_bugs.py

This imports the REAL project functions (not a re-typed copy) and asserts
the two bugs directly. Each assertion failing is the proof; if DeepStochLog
is later patched, these assertions will start passing and this script will
tell you so.
"""
from examples.anbncn.anbncn_data import create_anbncn_language
import tests.test_anbncn as test_anbncn_module
import tests.test_bracket as test_bracket_module


def prove_bug_1_min_length_rounds_down():
    """
    Bug 1: create_anbncn_language(min_length=4, ...) should NEVER return a
    string shorter than 4 characters. It does, because the code rounds a
    non-multiple-of-3 min_length DOWN to the nearest multiple of 3 instead
    of UP.
    """
    result = create_anbncn_language(min_length=4, max_length=9)
    shortest = min(len(s) for s in result)

    print(f"create_anbncn_language(min_length=4, max_length=9) -> {result}")
    print(f"Shortest string returned: {shortest} characters (requested minimum: 4)")

    assert shortest >= 4, (
        f"BUG CONFIRMED: asked for min_length=4, but got a string of length "
        f"{shortest} ('{min(result, key=len)}') in the result: {result}"
    )
    print("Bug 1 NOT present (this would only print if the code has been fixed).")


def prove_bug_2_duplicate_class_name():
    """
    Bug 2: tests/test_anbncn.py's test class is named `BracketTest`, an exact
    duplicate of the class name used in tests/test_bracket.py for a
    completely different language (parenthesis matching, not aⁿbⁿcⁿ).

    This proves two concrete consequences:
      (a) the names really do collide (same string, unrelated content)
      (b) an unaliased double-import silently discards the first class,
          with no error and no warning
    """
    name_anbncn = test_anbncn_module.BracketTest.__name__
    name_bracket = test_bracket_module.BracketTest.__name__
    print(f"tests/test_anbncn.py test class name:  {name_anbncn}")
    print(f"tests/test_bracket.py test class name: {name_bracket}")
    assert name_anbncn == name_bracket == "BracketTest", (
        "Expected both classes to be misleadingly named identically."
    )

    # Prove they are genuinely different, unrelated test suites sharing a name
    anbncn_tests = {m for m in dir(test_anbncn_module.BracketTest) if m.startswith("test_")}
    bracket_tests = {m for m in dir(test_bracket_module.BracketTest) if m.startswith("test_")}
    print(f"  -> test_anbncn.BracketTest test methods:  {sorted(anbncn_tests)}")
    print(f"  -> test_bracket.BracketTest test methods: {sorted(bracket_tests)}")
    assert anbncn_tests.isdisjoint(bracket_tests), (
        "Expected these to be two unrelated test suites that happen to share a class name."
    )

    # Simulate the realistic failure mode: an unaliased import of both,
    # e.g. in a script that does `from tests.test_anbncn import *` type usage,
    # or any tool that imports both modules' public names into one namespace.
    namespace = {}
    namespace["BracketTest"] = test_anbncn_module.BracketTest  # e.g. "import anbncn tests"
    first_binding = namespace["BracketTest"]
    namespace["BracketTest"] = test_bracket_module.BracketTest  # e.g. "import bracket tests too"
    second_binding = namespace["BracketTest"]

    print(f"  -> After importing both without aliasing, 'BracketTest' now resolves to: "
          f"{second_binding.__module__}.{second_binding.__name__}")
    print(f"     The anbncn version ({first_binding.__module__}.{first_binding.__name__}) "
          f"is gone from that namespace with NO error or warning.")

    assert first_binding is not second_binding, "Expected the two classes to be distinct objects."
    shadowed = namespace["BracketTest"].__module__ == "tests.test_bracket"
    assert not shadowed, (
        "BUG CONFIRMED: the anbncn BracketTest was silently shadowed and lost "
        "when both same-named classes were imported into one namespace, with "
        "no error or warning."
    )


def run(name, fn):
    print("=" * 70)
    print(f"PROOF: {name}")
    print("=" * 70)
    try:
        fn()
        print(f"RESULT: NOT REPRODUCED (assertions passed -- bug may be fixed)\n")
        return True
    except AssertionError as e:
        print(f"RESULT: BUG CONFIRMED -- {e}\n")
        return False


if __name__ == "__main__":
    results = {}
    results["Bug 1 (min_length rounds down)"] = run(
        "Bug 1 - create_anbncn_language() rounds min_length DOWN",
        prove_bug_1_min_length_rounds_down,
    )
    results["Bug 2 (duplicate BracketTest class name)"] = run(
        "Bug 2 - duplicate 'BracketTest' class name",
        prove_bug_2_duplicate_class_name,
    )

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, fixed in results.items():
        status = "not reproduced (fixed?)" if fixed else "BUG CONFIRMED"
        print(f"  {name}: {status}")
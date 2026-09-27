#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Combined proof-of-bugs script for tests/test_anbncn.py and the code it
exercises (examples/anbncn/anbncn_data.py) in ML-KULeuven/deepstochlog.

Run from anywhere:
    python prove_all_bugs.py
"""
import sys
from pathlib import Path

# This script lives at: .../deepstochlog_bug_reports/test_anbncn/prove_all_bugs.py
# The repo lives at:    .../deepstochlog/
# Both are siblings under the same parent folder, so we walk up from this
# script's own location and point Python at the repo -- no need to `cd`
# anywhere first, and no ModuleNotFoundError regardless of where you run it from.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from unittest.mock import patch

from examples.anbncn.anbncn_data import create_anbncn_language, create_non_anbncn_language
import examples.anbncn.anbncn_data as anbncn_data
import tests.test_anbncn as test_anbncn_module
import tests.test_bracket as test_bracket_module


def bug1_min_length_rounds_down():
    result = create_anbncn_language(min_length=4, max_length=9)
    shortest = min(len(s) for s in result)
    print(f"  create_anbncn_language(min_length=4, max_length=9) -> {result}")
    print(f"  Shortest string returned: {shortest} characters (requested minimum: 4)")
    assert shortest >= 4, (
        f"BUG CONFIRMED: asked for min_length=4, got a string of length {shortest} "
        f"('{min(result, key=len)}') in result: {result}"
    )


def bug2_duplicate_class_name():
    name_anbncn = test_anbncn_module.BracketTest.__name__
    name_bracket = test_bracket_module.BracketTest.__name__
    print(f"  tests/test_anbncn.py class name:  {name_anbncn}")
    print(f"  tests/test_bracket.py class name: {name_bracket}")
    assert name_anbncn == name_bracket == "BracketTest"

    namespace = {}
    namespace["BracketTest"] = test_anbncn_module.BracketTest
    first_binding = namespace["BracketTest"]
    namespace["BracketTest"] = test_bracket_module.BracketTest  # unaliased 2nd import
    second_binding = namespace["BracketTest"]

    print(f"  After importing both without aliasing, 'BracketTest' resolves to: "
          f"{second_binding.__module__}.{second_binding.__name__}")
    print(f"  The anbncn version ({first_binding.__module__}.{first_binding.__name__}) "
          f"is gone -- no error, no warning.")

    shadowed = namespace["BracketTest"].__module__ == "tests.test_bracket"
    assert not shadowed, "BUG CONFIRMED: the anbncn BracketTest was silently shadowed and lost."


def bug3_ignored_min_length():
    real_create_anbncn_language = anbncn_data.create_anbncn_language
    captured_calls = []

    def spy(*args, **kwargs):
        captured_calls.append(kwargs)
        return real_create_anbncn_language(*args, **kwargs)

    with patch.object(anbncn_data, "create_anbncn_language", side_effect=spy):
        create_non_anbncn_language(min_length=7, max_length=15)

    print(f"  Caller passed min_length=7 to create_non_anbncn_language.")
    print(f"  Internal call to create_anbncn_language was made with: {captured_calls}")

    assert captured_calls, "Expected an internal call to be captured."
    internal_min_length = captured_calls[0].get("min_length")
    assert internal_min_length == 7, (
        f"BUG CONFIRMED: caller's min_length=7 was ignored. Internal exclusion "
        f"set was built with min_length={internal_min_length} instead."
    )


def bug4_custom_letters_break_length():
    r = create_anbncn_language(min_length=3, max_length=9, letters=('aa', 'bb', 'cc'))
    lengths = [len(s) for s in r]
    print(f"  create_anbncn_language(min_length=3, max_length=9, letters=('aa','bb','cc'))")
    print(f"  -> {r}")
    print(f"  Actual lengths: {lengths} -- requested range: [3, 9]")
    assert all(3 <= L <= 9 for L in lengths), (
        f"BUG CONFIRMED: got strings of length {lengths}, but requested max_length=9."
    )


BUGS = [
    ("Bug 1 - min_length rounds DOWN instead of UP", bug1_min_length_rounds_down),
    ("Bug 2 - duplicate 'BracketTest' class name causes silent shadowing", bug2_duplicate_class_name),
    ("Bug 3 - caller's min_length silently ignored in internal default", bug3_ignored_min_length),
    ("Bug 4 - length filtering breaks for multi-character letters", bug4_custom_letters_break_length),
]


def main():
    results = []
    for name, fn in BUGS:
        print("=" * 70)
        print(f"PROOF: {name}")
        print("=" * 70)
        try:
            fn()
            print("RESULT: NOT REPRODUCED (assertions passed -- bug may be fixed)\n")
            results.append((name, "NOT REPRODUCED"))
        except AssertionError as e:
            print(f"RESULT: BUG CONFIRMED -- {e}\n")
            results.append((name, "BUG CONFIRMED"))

    print("=" * 70)
    print("SUMMARY -- tests/test_anbncn.py")
    print("=" * 70)
    for name, status in results:
        print(f"  [{status}] {name}")


if __name__ == "__main__":
    main()
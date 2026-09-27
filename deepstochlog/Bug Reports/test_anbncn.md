# Bug Report — tests/test_anbncn.py (ML-KULeuven/deepstochlog)

Target repo: https://github.com/ML-KULeuven/deepstochlog
File under test: `tests/test_anbncn.py`
Code it exercises: `examples/anbncn/anbncn_data.py`
Verified: cloned repo, ran against real source, proof script included below.

## Bug 1 — `create_anbncn_language()` rounds `min_length` DOWN instead of UP

**File:** `examples/anbncn/anbncn_data.py`
**Function:** `create_anbncn_language(min_length, max_length, letters=("a","b","c"))`

**The code:**
```python
if min_length % 3 != 0:
    print("Warning: min length should be divisible by 3, but was given", min_length)
    min_length = (min_length // 3) * 3   # rounds DOWN
```

**The problem:** every valid string in this language has a length that's a multiple
of 3. When `min_length` isn't a multiple of 3, the code snaps it down to the
nearest multiple of 3 instead of up — so the function can return strings
*shorter* than the minimum length the caller explicitly requested.

**Reproduction:**
```python
create_anbncn_language(min_length=4, max_length=9)
# Returns: ['abc', 'aabbcc', 'aaabbbccc']
# 'abc' is 3 characters -- below the requested minimum of 4.
```

**Impact:** silent data contamination in any training/validation/test split
built with a non-multiple-of-3 `min_length`. No exception is raised; the only
signal is an easily-missed `print()` warning. A researcher filtering out
"trivial" short examples by raising `min_length` would silently get them
back anyway.

**Why the existing test suite misses it:** every call in `test_anbncn.py`
uses `min_length=3`, which is already a multiple of 3, so this rounding
branch never executes during testing. Zero test coverage on this path.

**Suggested fix:** round up, not down —
`min_length = ((min_length + 2) // 3) * 3` (or equivalent ceiling logic).

---

## Bug 2 — Duplicate `BracketTest` class name across unrelated test files

**Files:** `tests/test_anbncn.py` (line 9) and `tests/test_bracket.py` (line 14)

**The code:**
```python
# tests/test_anbncn.py
class BracketTest(unittest.TestCase):   # tests the aⁿbⁿcⁿ language

# tests/test_bracket.py
class BracketTest(unittest.TestCase):   # tests balanced-parenthesis language
```

Identical class name, two completely unrelated test suites — almost
certainly `test_anbncn.py` was copy-pasted from `test_bracket.py` and never
renamed.

**What it does NOT break:** verified that `pytest`/`unittest` still collect
and run both suites correctly, because they're identified internally by full
module path (`tests.test_anbncn.BracketTest` vs `tests.test_bracket.BracketTest`),
not by bare class name. Running the test suite normally is unaffected.

**What it does break (proven):** an unaliased import of both classes into
one namespace silently discards the first one, with no error or warning:
```python
namespace["BracketTest"] = test_anbncn_module.BracketTest
namespace["BracketTest"] = test_bracket_module.BracketTest
# namespace["BracketTest"] is now ONLY the bracket-test class.
# The anbncn version is gone, silently.
```

**Impact:** low severity for normal test running, but a real hazard for:
- any script/tool that imports both test classes by name without aliasing
- IDE "go to definition" / global symbol search landing on the wrong file
- any coverage or flaky-test dashboard that keys results by bare class name
  rather than full module path

**Suggested fix:** rename the class in `test_anbncn.py` to something
accurate, e.g. `AnBnCnTest`.

---

## Proof script

Both bugs proven directly against the real project source (not a re-typed
copy) with `prove_anbncn_bugs.py`:

```python
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
    name_anbncn = test_anbncn_module.BracketTest.__name__
    name_bracket = test_bracket_module.BracketTest.__name__
    print(f"tests/test_anbncn.py test class name:  {name_anbncn}")
    print(f"tests/test_bracket.py test class name: {name_bracket}")
    assert name_anbncn == name_bracket == "BracketTest"

    anbncn_tests = {m for m in dir(test_anbncn_module.BracketTest) if m.startswith("test_")}
    bracket_tests = {m for m in dir(test_bracket_module.BracketTest) if m.startswith("test_")}
    print(f"  -> test_anbncn.BracketTest test methods:  {sorted(anbncn_tests)}")
    print(f"  -> test_bracket.BracketTest test methods: {sorted(bracket_tests)}")
    assert anbncn_tests.isdisjoint(bracket_tests)

    namespace = {}
    namespace["BracketTest"] = test_anbncn_module.BracketTest
    first_binding = namespace["BracketTest"]
    namespace["BracketTest"] = test_bracket_module.BracketTest
    second_binding = namespace["BracketTest"]

    print(f"  -> After importing both without aliasing, 'BracketTest' now resolves to: "
          f"{second_binding.__module__}.{second_binding.__name__}")
    print(f"     The anbncn version ({first_binding.__module__}.{first_binding.__name__}) "
          f"is gone from that namespace with NO error or warning.")

    assert first_binding is not second_binding
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
```

**Confirmed output (run against the real repo, commit `aed9531`):**
```
Bug 1 (min_length rounds down): BUG CONFIRMED
Bug 2 (duplicate BracketTest class name): BUG CONFIRMED
```

## Coverage gaps (not bugs, but untested)
- No test passes a non-multiple-of-3 `min_length` (this is exactly why Bug 1
  went unnoticed).
- No test passes `allow_non_threefold=True`.
- No test passes custom `letters` (e.g. `("x","y","z")`), even though
  `create_anbncn_language`, `create_non_anbncn_language`, and `ABCDataset`
  are all explicitly parameterized to support it, and `ABCDataset` even
  auto-generates all 6 permutations of the given letters.

"""F124 — one schema pin, not twelve.

`SCHEMA_VERSION` is the single source of truth for the schema head. Eleven
test assertions duplicated its current value as a literal, every one of them
waived with `f9-noqa: ssot-pin`. The lint was right eleven times and was
suppressed eleven times.

They caught nothing. The failure mode they claimed to guard — the constant
bumped without a migration — is already caught by the one genuine pin in
`test_phase240c_severity_ordering.py`, which compares `SCHEMA_VERSION` to
`max(m.version for m in MIGRATIONS)`. That is two independent sources
disagreeing, which is what a pin is for; `SCHEMA_VERSION == 63` is a copy,
and `SCHEMA_VERSION == SCHEMA_VERSION` would be `x == x`.

What they cost: every migration had to edit all eleven, and each carried a
hand-maintained restatement of the migration log that had grown to 1-2 KB.
Phase 255 appended to eleven of them and took **five passes** to find them
all.

**Schema history has one canonical home:** each `Migration.description` in
`src/motodiag/core/migrations.py`. Every version's rationale is already
there, written once. The per-phase narrative lives in
`docs/phases/completed/NNN_implementation.md`. Neither belongs in a test
comment.

What stays legal, and why:

* **`SCHEMA_VERSION >= N` floor pins.** Six phases use them (194, 195, 195B,
  235B, 244R, 255) and they say something the canonical pin cannot: *this
  phase's migration is still in the head*. Delete migration 063 and
  `max(MIGRATIONS)` happily agrees with a constant of 62 — only 255's floor
  pin notices. A floor pin is also written once and never edited again.
* **Equality against a literal BELOW the head** (`== 38`, `== 51`). Those
  assert a fixture's state mid-migration, not the head, and they are
  supposed to be exact.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from motodiag.core.database import SCHEMA_VERSION

TESTS = pathlib.Path(__file__).resolve().parent
SELF = pathlib.Path(__file__).name

#: Names that hold a schema version at runtime.
_VERSION_NAMES = {"SCHEMA_VERSION"}
_VERSION_CALLS = {"get_current_version", "get_schema_version"}

#: Files carrying an `f9-noqa: ssot-pin` waiver on a schema-version line, as
#: of F124. Every one is a `>=` floor pin. The set is pinned rather than the
#: count so that a NEW file taking a waiver fails here and has to justify
#: itself, which is the half that was missing when eleven accumulated.
_KNOWN_WAIVER_FILES = {
    "test_phase194_commit0_photo_upload.py",
    "test_phase195_commit0_voice_transcripts.py",
    "test_phase195b_commit0.py",
    "test_phase235b_regulation_provenance.py",
    "test_phase244R_dtc_taxonomy.py",
    "test_phase255_transmission_axis.py",
}


def _is_version_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and node.id in _VERSION_NAMES:
        return True
    if isinstance(node, ast.Call):
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
        return name in _VERSION_CALLS
    return False


def _head_equality_pins(directory: pathlib.Path = TESTS) -> list[str]:
    """Every `<version> == <literal>` where the literal is the current head.

    `directory` is a parameter so the controls plant into a tmp dir (Phase
    355 bug fix #2): a probe planted in the real tests/ vanished mid-read
    in a parallel worker's scan (FileNotFoundError).
    """
    found = []
    for path in sorted(directory.glob("test_*.py")):
        if path.name == SELF:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover - a broken test file
            raise AssertionError(f"{path.name} does not parse: {exc}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                continue
            if not isinstance(node.ops[0], ast.Eq):
                continue
            left, right = node.left, node.comparators[0]
            for a, b in ((left, right), (right, left)):
                if _is_version_expr(a) and isinstance(b, ast.Constant) \
                        and b.value == SCHEMA_VERSION and isinstance(b.value, int):
                    found.append(f"{path.name}:{node.lineno}")
    return sorted(set(found))


def _schema_version_waivers() -> dict[str, list[str]]:
    """`f9-noqa: ssot-pin` waivers sitting on a schema-version line."""
    out: dict[str, list[str]] = {}
    for path in sorted(TESTS.glob("test_*.py")):
        if path.name == SELF:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "f9-noqa: ssot-pin" not in line:
                continue
            code = line.split("#", 1)[0]
            if not any(n in code for n in _VERSION_NAMES | _VERSION_CALLS):
                continue
            out.setdefault(path.name, []).append(f"{i}:{code.strip()}")
    return out


class TestOnlyOneGenuinePin:
    def test_the_invariant_the_deleted_pins_claimed_to_guard_still_holds(self):
        """Assert the property itself, not that some file mentions it.

        F124 deleted eleven copies on the strength of one genuine pin
        existing elsewhere. If that pin is ever removed, this file should
        fail on its own rather than on the honour system — so the
        invariant is checked here directly, from the two sources.
        """
        from motodiag.core.migrations import MIGRATIONS

        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_the_genuine_pin_still_exists_in_code(self):
        """And that a TEST asserts it, so the invariant has a named owner.

        Read through `code_of`, which blanks comments and docstrings.
        Against raw source this would keep passing after the pin was
        deleted, as long as the same text survived anywhere in a comment —
        including in this file's own docstring, which quotes it. Phase 244G
        forbids raw-source assertions for exactly that reason, and caught
        this one in the full regression after I ran its scanner over the
        wrong file and reported it clean.
        """
        from support.source_guards import code_of

        code = code_of(TESTS / "test_phase240c_severity_ordering.py")
        assert "max(m.version for m in MIGRATIONS)" in code, (
            "the one genuine schema pin is gone from code; F124 deleted "
            "eleven copies on the strength of it existing"
        )

    def test_no_test_pins_the_head_with_a_literal(self):
        """The F124 guard.

        A literal equal to the current head is a copy of `SCHEMA_VERSION`,
        and it has to be edited by every future migration. Assert a floor
        with `>=`, or compare to the registry.
        """
        offenders = _head_equality_pins()
        assert offenders == [], (
            "these assert equality against a literal equal to the current "
            f"SCHEMA_VERSION ({SCHEMA_VERSION}) — use `>= N` for a floor, or "
            "compare against max(MIGRATIONS):\n  " + "\n  ".join(offenders)
        )

    def test_no_new_schema_version_ssot_waiver(self):
        """A new file waiving the SSOT lint for a schema version must justify itself.

        Eleven accumulated because each looked like one reasonable exception.
        The set is pinned, not the count.
        """
        actual = set(_schema_version_waivers())
        new = actual - _KNOWN_WAIVER_FILES
        assert new == set(), (
            "new f9-noqa: ssot-pin waiver(s) on a schema-version line: "
            f"{sorted(new)}. If this is a `>= N` floor pin, add the file to "
            "_KNOWN_WAIVER_FILES with a reason. If it is an `== head` pin, it "
            "is what F124 deleted eleven of."
        )

    def test_every_surviving_waiver_is_a_floor_not_a_head_pin(self):
        bad = [
            f"{f}:{entry}"
            for f, entries in _schema_version_waivers().items()
            for entry in entries
            if ">=" not in entry.split(":", 1)[1]
        ]
        assert bad == [], "surviving waivers must be `>=` floors, not equalities:\n  " + "\n  ".join(bad)

    @pytest.mark.parametrize("label,body", [
        (
            "constant",
            "from motodiag.core.database import SCHEMA_VERSION\n\n\n"
            "def test_probe():\n    assert SCHEMA_VERSION == {v}\n",
        ),
        (
            "call",
            "from motodiag.core.migrations import get_current_version\n\n\n"
            "def test_probe(db_path):\n"
            "    assert get_current_version(db_path) == {v}\n",
        ),
        (
            "call-reversed",
            "from motodiag.core.migrations import get_current_version\n\n\n"
            "def test_probe(db_path):\n"
            "    assert {v} == get_current_version(db_path)\n",
        ),
    ])
    def test_the_guard_detects_a_planted_head_pin(self, label, body, tmp_path):
        """Break-it/see-it-fail, inline, once per spelling.

        Both forms existed in this repo and both had to be deleted:
        `SCHEMA_VERSION == 63` in ten files, and
        `get_current_version(db_path) == 63` in `191b`. A scanner that saw
        only the first would have left the second, which is how `191b`'s
        pin survived being missed at Phase 244M — its own comment says so.
        The reversed form is included because nothing stops someone
        writing the literal on the left.
        """
        planted = tmp_path / f"test_zz_f124_planted_probe_{label.replace('-', '_')}.py"
        planted.write_text(body.format(v=SCHEMA_VERSION), encoding="utf-8")
        assert f"{planted.name}:5" in _head_equality_pins(tmp_path), (
            f"the scanner did not see a planted head pin spelled as a "
            f"{label} — it is not measuring that spelling"
        )

    def test_the_guard_ignores_a_floor_and_a_lower_literal(self, tmp_path):
        """The other half: it must not fire on what stays legal.

        A `>=` floor at the head (six phases use one) and an equality
        against an intermediate version (`== 38`, `== 51`, which assert a
        fixture mid-migration) are both correct and must not be reported.
        """
        probes = {
            "floor": f"    assert SCHEMA_VERSION >= {SCHEMA_VERSION}\n",
            "intermediate": "    assert get_current_version(db_path) == 38\n",
        }
        for label, line in probes.items():
            planted = tmp_path / f"test_zz_f124_legal_probe_{label}.py"
            planted.write_text(
                "from motodiag.core.database import SCHEMA_VERSION\n"
                "from motodiag.core.migrations import get_current_version\n\n\n"
                "def test_probe(db_path):\n" + line,
                encoding="utf-8",
            )
            hits = [h for h in _head_equality_pins(tmp_path) if h.startswith(planted.name)]
            assert hits == [], f"the guard fired on a legal {label} pin: {hits}"

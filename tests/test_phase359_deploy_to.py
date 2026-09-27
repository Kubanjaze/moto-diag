"""Phase 359 — the deploy scope's `to`: a changed field must hold exactly
the value the scope names.

The operator's condition on live row 4615: "the dry-run diff shows 4615
changing only to its seed text, field for field, and nothing else." The
scope's `fields` already hold "nothing else"; `to` holds "only to its seed
text". Fixture databases only, 358's harness.
"""

from __future__ import annotations

import copy
import json

import pytest

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, SCOPE, _commit_diff, _dryrun, _git, _refusal, env, migrate_in_scope,
)


def _scope_with_to(env, value: str) -> None:
    scope = copy.deepcopy(SCOPE)
    scope["tables"]["checklist_items"]["changed"][0]["to"] = {"instruction_text": value}
    D.scope_path(env["repo"], PHASE).write_text(json.dumps(scope, indent=1))
    _git(env["repo"], "add", "-A")
    _git(env["repo"], "commit", "-qm", "scope with to")


def test_the_value_the_migration_writes_passes(env):
    _scope_with_to(env, "check the thing, sourced")
    assert _dryrun(env) == 0
    assert D._header(D.diff_path(env["repo"], PHASE).read_text())["Scope problems"] == "none"


def test_any_other_value_is_a_scope_problem_and_the_apply_refuses(env, capsys):
    """The known-bad case: the row changes only in its allowed field, but
    not to the named text. `fields` alone passes this; `to` must not."""
    _scope_with_to(env, "check the thing, sourced from the seed")
    assert _dryrun(env) == 1
    head = D._header(D.diff_path(env["repo"], PHASE).read_text())
    assert "instruction_text is not the scope's 'to' value" in head["Scope problems"]
    _commit_diff(env)
    assert "scope problems" in _refusal(env, capsys)


def test_without_to_the_same_migration_passes(env):
    """The control: the plain scope accepts the migration, so the refusal
    above is `to`'s doing."""
    assert _dryrun(env, migrate_in_scope) == 0


@pytest.mark.parametrize("value", ["check the thing, sourced"])
def test_check_scope_reads_the_value_by_column_name(env, value):
    before = D.dump(env["live"])
    import shutil
    after_path = env["live"].with_name("after.db")
    shutil.copy(env["live"], after_path)
    migrate_in_scope(after_path)
    d = D.diff(before, D.dump(after_path))
    allowed = D.resolve(SCOPE, env["live"])
    rowid = next(iter(allowed["checklist_items"]))
    assert D.check_scope(d, SCOPE, allowed, {"checklist_items": {rowid: {"instruction_text": value}}}) == []
    assert D.check_scope(d, SCOPE, allowed, {"checklist_items": {rowid: {"instruction_text": "x"}}})

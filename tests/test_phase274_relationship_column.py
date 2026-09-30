"""Phase 274 bug fix #1 — `shop customer bikes` and `show` printed `?` for
every relationship.

`list_bikes_for_customer` returns the link's relationship as
`cb_relationship` (the vehicle row has its own columns), and both tables
read `relationship`. Found at Step 0 (S0-2).
"""

from __future__ import annotations

import pytest

from support.phase274 import new_db, ok, seed_bike, seed_customer, seed_shop


@pytest.mark.parametrize("command", ["bikes", "show"])
def test_the_relationship_is_printed(tmp_path, command):
    db = new_db(tmp_path)
    seed_customer(db, seed_shop(db), "Dana Reyes")
    seed_bike(db)
    ok(db, "shop", "customer", "link-bike", "2", "--bike", "1",
       "--relationship", "previous_owner")
    out = ok(db, "shop", "customer", command, "2")
    assert "previous_owner" in out
    assert "│ ?" not in out

"""Phase 303 — the tier a session caller meets (the operator's answer to part
(c) of the stop).

The operator's words: "A logged-in staff member uses their own
subscription, else the highest active subscription of an owner-role active
member of a shop they are an active member of." A key caller is resolved
exactly as before. The other reading, (ii), would change the rule for
every caller, keys included; the control below shows the two differ.
"""

from __future__ import annotations

import pytest

from motodiag.auth.api_key_repo import create_api_key
from motodiag.auth.deps import resolve_tier
from motodiag.auth.sessions_repo import create_session
from motodiag.shop.rbac import deactivate_member

from support.phase303 import add_member, make_shop, make_sub, make_user, new_db, sql


@pytest.fixture
def db(tmp_path, monkeypatch):
    return new_db(tmp_path, monkeypatch)


def _session(db, uid):
    return create_session(uid, db_path=db)[0]


def _key(db, uid):
    return create_api_key(uid, db_path=db)[0]


@pytest.fixture
def tech(db):
    olga = make_user(db, "olga")
    make_sub(db, olga, "shop")
    a = make_shop(db, "Shop A", olga)
    tess = make_user(db, "tess")
    add_member(db, a, tess)
    return {"olga": olga, "a": a, "tess": tess}


def test_a_session_with_no_subscription_meets_its_owners(db, tech):
    assert resolve_tier(_session(db, tech["tess"]), db_path=db) == "shop"


def test_the_control_a_key_for_the_same_tech_meets_none(db, tech):
    """Reading (ii) would give this key "shop" too; the operator's does not."""
    assert resolve_tier(_key(db, tech["tess"]), db_path=db) is None


def test_the_callers_own_subscription_comes_first(db, tech):
    make_sub(db, tech["tess"], "individual")
    assert resolve_tier(_session(db, tech["tess"]), db_path=db) == "individual"
    assert resolve_tier(_key(db, tech["tess"]), db_path=db) == "individual"


def test_the_highest_across_every_shop(db, tech):
    cara = make_user(db, "cara")
    make_sub(db, cara, "company")
    b = make_shop(db, "Shop B", cara)
    add_member(db, b, tech["tess"], "service_writer")
    assert resolve_tier(_session(db, tech["tess"]), db_path=db) == "company"


def test_a_non_owner_members_subscription_does_not_count(db, tech):
    rich = make_user(db, "rich")
    make_sub(db, rich, "company")
    add_member(db, tech["a"], rich, "tech")
    assert resolve_tier(_session(db, tech["tess"]), db_path=db) == "shop"


def test_an_inactive_membership_of_the_caller_does_not_count(db, tech):
    deactivate_member(tech["a"], tech["tess"], db_path=db)
    assert resolve_tier(_session(db, tech["tess"]), db_path=db) is None


def test_an_inactive_owner_does_not_count(db, tech):
    deactivate_member(tech["a"], tech["olga"], db_path=db)
    assert resolve_tier(_session(db, tech["tess"]), db_path=db) is None


def test_an_owners_cancelled_subscription_does_not_count(db, tech):
    sql(db, "UPDATE subscriptions SET status = 'canceled' WHERE user_id = ?", (tech["olga"],))
    assert resolve_tier(_session(db, tech["tess"]), db_path=db) is None


def test_a_key_callers_tier_is_unchanged_for_an_owner(db, tech):
    assert resolve_tier(_key(db, tech["olga"]), db_path=db) == "shop"
    assert resolve_tier(_session(db, tech["olga"]), db_path=db) == "shop"

"""Phase 207 — security audit findings, pinned as tests.

Each class corresponds to a finding. Live probes against the running
server informed these; the tests are the durable form.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db

#: Larger than SQLite's 64-bit signed integer, so binding it raises
#: OverflowError inside the repo layer.
OVERSIZED_ID = 999999999999999999999999


@pytest.fixture
def api(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "sec.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    with get_connection(path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES ('sec', 'sec@ex.com', 'company', 1)",
        ).lastrowid
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, "
            " current_period_end) VALUES (?, 'company', 'active', "
            " datetime('now', '+30 days'))", (uid,),
        )
        sid = conn.execute(
            "INSERT INTO diagnostic_sessions (vehicle_make, vehicle_model,"
            " vehicle_year, status, user_id) "
            "VALUES ('Honda','CB',2020,'open',?)", (uid,),
        ).lastrowid
    _, key = create_api_key(uid, db_path=path)
    client = TestClient(
        create_app(db_path_override=path), raise_server_exceptions=False,
    )
    yield client, key, uid, sid
    reset_settings()


class TestOversizedIdIsInvalidInputNotAServerFault:
    """An id beyond SQLite's 64-bit range reached the database before
    anything rejected it, raising OverflowError and surfacing as a 500
    with a full stack trace in the log — on every route family with an
    integer id.

    Nothing leaked to the client, but it let any key-holder fill the
    error log, and it broke the pattern its neighbours follow.
    """

    @pytest.mark.parametrize("path", [
        f"/v1/sessions/{OVERSIZED_ID}",
        f"/v1/reports/session/{OVERSIZED_ID}",
        f"/v1/sessions/{OVERSIZED_ID}/videos",
        f"/v1/shop/{OVERSIZED_ID}/work-orders",
    ])
    def test_oversized_id_is_422_not_500(self, api, path):
        client, key, _uid, _sid = api
        r = client.get(path, headers={"X-API-Key": key})
        assert r.status_code == 422, (
            f"{path} returned {r.status_code}; an unparseable id must "
            "not reach the database"
        )

    def test_the_response_says_nothing_about_internals(self, api):
        client, key, _uid, _sid = api
        r = client.get(
            f"/v1/sessions/{OVERSIZED_ID}", headers={"X-API-Key": key},
        )
        body = r.text.lower()
        for leak in ("sqlite", "traceback", "overflowerror", "site-packages"):
            assert leak not in body, f"response leaks {leak!r}"

    def test_neighbouring_id_shapes_are_unchanged(self, api):
        """The fix must not move behaviour it was not aimed at. A
        non-numeric id was already 422 and a negative one 404; only the
        oversized case was out of line."""
        client, key, _uid, sid = api
        assert client.get(
            "/v1/sessions/abc", headers={"X-API-Key": key},
        ).status_code == 422
        assert client.get(
            "/v1/sessions/-5", headers={"X-API-Key": key},
        ).status_code == 404
        assert client.get(
            f"/v1/sessions/{sid}", headers={"X-API-Key": key},
        ).status_code == 200


class TestAuthenticationBasics:

    @pytest.mark.parametrize("headers", [
        {},
        {"X-API-Key": ""},
        {"X-API-Key": "mdk_live_not_a_real_key"},
        {"X-API-Key": "garbage"},
    ])
    def test_no_valid_key_means_401(self, api, headers):
        client, _key, _uid, _sid = api
        assert client.get("/v1/sessions", headers=headers).status_code == 401


class TestCrossUserIsolation:
    """A second user must not reach the first user's session-scoped data
    by changing the id in the path."""

    def _second_user(self, db_path):
        with get_connection(db_path) as conn:
            uid = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES ('other', 'other@ex.com', 'company', 1)",
            ).lastrowid
            conn.execute(
                "INSERT INTO subscriptions (user_id, tier, status, "
                " current_period_end) VALUES (?, 'company', 'active', "
                " datetime('now', '+30 days'))", (uid,),
            )
        return uid

    @pytest.mark.parametrize("template", [
        "/v1/sessions/{sid}",
        "/v1/reports/session/{sid}",
        "/v1/sessions/{sid}/videos",
    ])
    def test_another_user_cannot_read_the_session(
        self, api, tmp_path, template,
    ):
        client, key, _uid, sid = api
        db_path = str(tmp_path / "sec.db")
        other = self._second_user(db_path)
        _, other_key = create_api_key(other, db_path=db_path)

        path = template.format(sid=sid)
        assert client.get(
            path, headers={"X-API-Key": key},
        ).status_code == 200, "owner should be able to read it"
        assert client.get(
            path, headers={"X-API-Key": other_key},
        ).status_code in (403, 404), f"{path} is reachable cross-user"

    def test_another_user_cannot_mint_a_share_link(self, api, tmp_path):
        """Phase 200 links are capability URLs — minting one for someone
        else's session would hand over their report permanently."""
        client, _key, _uid, sid = api
        db_path = str(tmp_path / "sec.db")
        other = self._second_user(db_path)
        _, other_key = create_api_key(other, db_path=db_path)
        r = client.post(
            f"/v1/reports/session/{sid}/share",
            json={}, headers={"X-API-Key": other_key},
        )
        assert r.status_code in (403, 404)


class TestSearchInputIsParameterised:
    """Search terms reach SQL as bound parameters, so quotes and
    statement separators are literal text, not syntax."""

    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "'; DROP TABLE known_issues;--",
        "%' UNION SELECT null,null--",
        '" OR 1=1 --',
    ])
    def test_injection_payloads_are_treated_as_text(self, api, payload):
        client, key, _uid, _sid = api
        r = client.get(
            "/v1/kb/issues", params={"q": payload},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        # Treated as a literal search string, so it matches nothing.
        assert r.json()["items"] == []

    def test_the_table_survives(self, api, tmp_path):
        client, key, _uid, _sid = api
        client.get(
            "/v1/kb/issues", params={"q": "'; DROP TABLE known_issues;--"},
            headers={"X-API-Key": key},
        )
        with get_connection(str(tmp_path / "sec.db")) as conn:
            # The table still answers; a successful DROP would raise.
            conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()


class TestPublicShareRouteIsNotAnOpenDoor:
    """`/v1/share/{token}` is unauthenticated by design, so its
    boundaries are the whole security model."""

    @pytest.mark.parametrize("token", [
        "a" * 43,
        "../../etc/passwd",
        "' OR 1=1--",
        "",
    ])
    def test_unknown_tokens_do_not_resolve(self, api, token):
        client, _key, _uid, _sid = api
        r = client.get(f"/v1/share/{token}")
        assert r.status_code in (404, 405, 307), r.status_code
        assert "PRIVATE" not in r.text.upper()


# ---------------------------------------------------------------------------
# Finding 1 (critical) — customer records were not scoped to a shop
# ---------------------------------------------------------------------------


@pytest.fixture
def two_shops(tmp_path, monkeypatch):
    """Two shops, each with its own member and its own customer.

    The attacker is a legitimate, paying, active member of shop A and
    of nothing else. That is the whole setup — no token guessing, no
    race, no privilege escalation.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "tenancy.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()

    made = {}
    with get_connection(path) as conn:
        for label in ("a", "b"):
            uid = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                f"VALUES ('user_{label}', '{label}@ex.com', 'shop', 1)",
            ).lastrowid
            conn.execute(
                "INSERT INTO subscriptions (user_id, tier, status, "
                " current_period_end) VALUES (?, 'shop', 'active', "
                " datetime('now', '+30 days'))", (uid,),
            )
            shop_id = conn.execute(
                "INSERT INTO shops (name, owner_user_id) VALUES (?, ?)",
                (f"Shop {label.upper()}", uid),
            ).lastrowid
            conn.execute(
                "INSERT INTO shop_members (user_id, shop_id, role, "
                " is_active) VALUES (?, ?, 'owner', 1)", (uid, shop_id),
            )
            cid = conn.execute(
                "INSERT INTO customers (name, email, phone, notes, shop_id)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    f"Customer {label.upper()}",
                    f"cust_{label}@ex.com",
                    f"555-000{label}",
                    f"private note {label}",
                    shop_id,
                ),
            ).lastrowid
            made[label] = {"uid": uid, "shop_id": shop_id, "cid": cid}

    for label in ("a", "b"):
        _, made[label]["key"] = create_api_key(
            made[label]["uid"], db_path=path,
        )

    client = TestClient(
        create_app(db_path_override=path), raise_server_exceptions=False,
    )
    yield client, made, path
    reset_settings()


class TestCustomerRecordsAreScopedToTheirShop:
    """`GET /v1/shop/{shop_id}/customers` listed the customers table
    unfiltered. `require_shop_access` confirmed the caller belonged to
    the shop in the URL and then the query ignored the shop entirely,
    so one active membership returned every customer row in the
    database: name, email, phone, address, shop-private notes.

    The column that was supposed to prevent this (`owner_user_id`) was
    never set by any caller, so every row held its DEFAULT of 1.
    """

    def test_list_returns_only_this_shops_customers(self, two_shops):
        client, made, _ = two_shops
        r = client.get(
            f"/v1/shop/{made['a']['shop_id']}/customers",
            headers={"X-API-Key": made["a"]["key"]},
        )
        assert r.status_code == 200
        names = {row["name"] for row in r.json()["items"]}
        assert names == {"Customer A"}, (
            f"shop A's member sees {names}; membership in one shop is "
            "not entitlement to another shop's customer list"
        )

    def test_no_other_shops_pii_appears_anywhere_in_the_body(
        self, two_shops,
    ):
        client, made, _ = two_shops
        r = client.get(
            f"/v1/shop/{made['a']['shop_id']}/customers",
            headers={"X-API-Key": made["a"]["key"]},
        )
        body = r.text
        for leaked in ("cust_b@ex.com", "555-000b", "private note b"):
            assert leaked not in body, f"leaked {leaked!r}"

    def test_fetching_another_shops_customer_by_id_is_404(self, two_shops):
        client, made, _ = two_shops
        r = client.get(
            f"/v1/shop/{made['a']['shop_id']}/customers/{made['b']['cid']}",
            headers={"X-API-Key": made["a"]["key"]},
        )
        assert r.status_code == 404

    def test_404_does_not_distinguish_existing_from_absent(self, two_shops):
        """Otherwise the status code alone confirms which ids are real."""
        client, made, _ = two_shops
        real_other = client.get(
            f"/v1/shop/{made['a']['shop_id']}/customers/{made['b']['cid']}",
            headers={"X-API-Key": made["a"]["key"]},
        )
        never_existed = client.get(
            f"/v1/shop/{made['a']['shop_id']}/customers/999999",
            headers={"X-API-Key": made["a"]["key"]},
        )
        assert real_other.status_code == never_existed.status_code == 404

    def test_created_customers_are_bound_to_the_creating_shop(
        self, two_shops,
    ):
        """The POST built a Customer without shop_id, so new rows were
        as unscoped as the legacy ones."""
        client, made, path = two_shops
        r = client.post(
            f"/v1/shop/{made['a']['shop_id']}/customers",
            headers={"X-API-Key": made["a"]["key"]},
            json={"name": "Fresh Customer"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["shop_id"] == made["a"]["shop_id"]

        seen = client.get(
            f"/v1/shop/{made['b']['shop_id']}/customers",
            headers={"X-API-Key": made["b"]["key"]},
        ).json()["items"]
        assert "Fresh Customer" not in {row["name"] for row in seen}

    def test_intake_rejects_a_customer_from_another_shop(self, two_shops):
        """customer_id comes from the request body, so the intake route
        would otherwise bind — and confirm the existence of — another
        shop's customer id."""
        client, made, _ = two_shops
        r = client.post(
            f"/v1/shop/{made['a']['shop_id']}/intakes",
            headers={"X-API-Key": made["a"]["key"]},
            json={
                "customer_id": made["b"]["cid"],
                "vehicle_id": 1,
                "reported_problems": "probe",
            },
        )
        assert r.status_code == 404, (
            f"intake accepted another shop's customer id ({r.status_code})"
        )

    def test_unclaimed_rows_belong_to_no_shop(self, two_shops):
        """A NULL shop_id must match no shop rather than every shop —
        `= ?` is never true for NULL, which is the safe direction."""
        client, made, path = two_shops
        with get_connection(path) as conn:
            orphan = conn.execute(
                "INSERT INTO customers (name, shop_id) "
                "VALUES ('Orphan', NULL)",
            ).lastrowid
        for label in ("a", "b"):
            rows = client.get(
                f"/v1/shop/{made[label]['shop_id']}/customers",
                headers={"X-API-Key": made[label]["key"]},
            ).json()["items"]
            assert "Orphan" not in {row["name"] for row in rows}
            assert client.get(
                f"/v1/shop/{made[label]['shop_id']}/customers/{orphan}",
                headers={"X-API-Key": made[label]["key"]},
            ).status_code == 404


class TestProductionRefusesTheFakeBillingProvider:
    """`billing_provider` defaults to "fake". That provider verifies a
    webhook by comparing the header to a hardcoded literal, the webhook
    route takes no API key, and it sits on the rate-limit exempt list.
    Tier is then read straight out of the event metadata — so a single
    forged `checkout.session.completed` grants a paid subscription.

    Nothing in the code prevented that default from reaching
    production; it relied on the deploy remembering an env var.
    """

    def test_prod_with_the_fake_provider_will_not_start(self):
        from motodiag.core.config import Environment, Settings

        with pytest.raises(RuntimeError, match="billing_provider"):
            create_app(Settings(env=Environment.PROD,
                                billing_provider="fake"))

    def test_prod_with_stripe_starts(self):
        from motodiag.core.config import Environment, Settings

        create_app(Settings(env=Environment.PROD,
                            billing_provider="stripe"))

    def test_dev_still_starts_on_the_fake_provider(self):
        """Local work must not need Stripe credentials."""
        from motodiag.core.config import Environment, Settings

        create_app(Settings(env=Environment.DEV, billing_provider="fake"))


class TestRejectedInputIsNotWrittenToTheLog:
    """The 422 handler logged `exc.errors()` at WARNING. Under pydantic
    v2 each entry carries an `input` key holding the rejected value,
    and on a model-level failure that is the entire request body — so
    validation failures wrote user data into the log verbatim.
    """

    def test_the_rejected_value_is_absent_from_the_log(self, api, caplog):
        import logging

        client, key, _uid, _sid = api
        secret = "TOO-SHORT-abc"  # under min_length=16
        with caplog.at_level(logging.WARNING):
            r = client.post(
                "/v1/push/register",
                headers={"X-API-Key": key},
                json={"token": secret, "platform": "ios"},
            )
        assert r.status_code == 422, r.text
        assert secret not in caplog.text, (
            "the rejected value reached the log"
        )

    def test_the_diagnostic_shape_is_still_logged(self, api, caplog):
        """Redaction must not cost the reason the request failed."""
        import logging

        client, key, _uid, _sid = api
        with caplog.at_level(logging.WARNING):
            client.post(
                "/v1/push/register",
                headers={"X-API-Key": key},
                json={"token": "tiny", "platform": "ios"},
            )
        assert "422 validation failure" in caplog.text
        assert "token" in caplog.text  # which field
        assert "/v1/push/register" in caplog.text  # which route


class TestPushDeregistrationIsScopedToTheCaller:
    """`delete_token` deleted by token alone, so any authenticated user
    who learned another user's device token could silence that user's
    notifications. Registration was already bound to the user; only the
    delete side was missing the check.
    """

    def test_a_user_cannot_deregister_another_users_token(self, tmp_path):
        from motodiag.push.registry import delete_token, register_token

        path = str(tmp_path / "push.db")
        init_db(path)
        with get_connection(path) as conn:
            victim = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES ('victim', 'v@ex.com', 'shop', 1)",
            ).lastrowid
            attacker = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES ('attacker', 'a@ex.com', 'shop', 1)",
            ).lastrowid

        token = "a" * 64
        register_token(victim, token, "ios", db_path=path)

        assert delete_token(token, db_path=path, user_id=attacker) is False
        assert delete_token(token, db_path=path, user_id=victim) is True

    def test_the_unscoped_form_still_works_for_the_apns_prune(
        self, tmp_path,
    ):
        """APNs returns 410 for a dead token with no user context, so
        that path must stay able to delete by token alone."""
        from motodiag.push.registry import delete_token, register_token

        path = str(tmp_path / "prune.db")
        init_db(path)
        with get_connection(path) as conn:
            uid = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES ('u', 'u@ex.com', 'shop', 1)",
            ).lastrowid
        token = "b" * 64
        register_token(uid, token, "ios", db_path=path)
        assert delete_token(token, db_path=path) is True


class TestUploadsAreBoundedPerRequest:
    """Both media routes called `await file.read()` and only then
    consulted their quota helpers. Those quotas are per-session and
    per-work-order *aggregates*, so nothing bounded a single body: one
    arbitrarily large POST was materialised in full first, and the
    check that was meant to stop it ran afterwards.
    """

    @pytest.mark.anyio
    async def test_an_oversized_stream_is_refused_mid_read(self):
        from motodiag.api.uploads import UploadTooLargeError, read_bounded

        class _Endless:
            """A body that never ends — the unbounded case."""
            def __init__(self):
                self.served = 0

            async def read(self, size: int = -1) -> bytes:
                self.served += size
                return b"\0" * size

        stream = _Endless()
        limit = 4 * 1024 * 1024
        with pytest.raises(UploadTooLargeError):
            await read_bounded(stream, limit)  # type: ignore[arg-type]
        assert stream.served <= limit + 1024 * 1024, (
            "read past the ceiling before stopping"
        )

    @pytest.mark.anyio
    async def test_a_body_within_the_limit_round_trips_intact(self):
        from motodiag.api.uploads import read_bounded

        payload = b"x" * (3 * 1024 * 1024 + 17)

        class _Fixed:
            def __init__(self, data): self.data, self.pos = data, 0
            async def read(self, size: int = -1) -> bytes:
                chunk = self.data[self.pos:self.pos + size]
                self.pos += len(chunk)
                return chunk

        got = await read_bounded(_Fixed(payload), 8 * 1024 * 1024)  # type: ignore[arg-type]
        assert got == payload

    @pytest.mark.anyio
    async def test_a_declared_length_over_the_limit_is_refused_early(self):
        """Content-Length is a hint, not a guarantee — but when it is
        already over the ceiling there is no reason to read at all."""
        from motodiag.api.uploads import UploadTooLargeError, read_bounded

        class _NeverRead:
            async def read(self, size: int = -1) -> bytes:
                raise AssertionError("should not have been read")

        with pytest.raises(UploadTooLargeError):
            await read_bounded(
                _NeverRead(), 1024, declared_length=99999,  # type: ignore[arg-type]
            )

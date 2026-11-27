"""Phase 329 prebuild: one-time codes for an email link, and the stand-in
email sender. No storage, no routes, no network, no real email service."""

from __future__ import annotations

import pytest

from motodiag.auth.email_sender import (
    Email,
    EmailNotConfigured,
    FakeEmailSender,
    address_check_email,
    get_email_sender,
    password_reset_email,
)
from motodiag.auth.one_time_codes import (
    LIFETIME_S,
    PURPOSES,
    check_code,
    hash_code,
    issue_code,
)

T0 = 1_700_000_000.0


class TestIssue:

    def test_code_is_long_random_and_only_its_hash_is_kept(self):
        a = issue_code("verify_email", "7", now=T0)
        b = issue_code("verify_email", "7", now=T0)
        assert a.code != b.code
        assert len(a.code) >= 43
        assert a.record.code_hash == hash_code(a.code)
        assert a.code not in repr(a.record)

    @pytest.mark.parametrize("purpose,hours", [("verify_email", 24),
                                               ("reset_password", 1)])
    def test_lifetimes(self, purpose, hours):
        rec = issue_code(purpose, "7", now=T0).record
        assert rec.expires_at - rec.issued_at == hours * 3600

    def test_the_purposes_are_exactly_two(self):
        assert set(PURPOSES) == set(LIFETIME_S) == {"verify_email",
                                                    "reset_password"}

    def test_unknown_purpose_or_empty_subject_refused(self):
        with pytest.raises(ValueError):
            issue_code("login", "7", now=T0)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            issue_code("verify_email", "", now=T0)


class TestCheck:

    def _issued(self, purpose="verify_email", subject="7"):
        return issue_code(purpose, subject, now=T0)

    def test_right_code_works_once(self):
        i = self._issued()
        first = check_code(i.record, i.code, purpose="verify_email",
                           subject="7", now=T0 + 60)
        assert first.ok and first.record.used_at == T0 + 60
        again = check_code(first.record, i.code, purpose="verify_email",
                           subject="7", now=T0 + 61)
        assert again.outcome == "used"

    def test_wrong_code(self):
        i = self._issued()
        r = check_code(i.record, i.code[:-1] + ("A" if i.code[-1] != "A" else "B"),
                       purpose="verify_email", subject="7", now=T0)
        assert r.outcome == "wrong_code" and r.record == i.record
        assert check_code(i.record, "", purpose="verify_email",
                          subject="7", now=T0).outcome == "wrong_code"

    def test_expires_at_its_lifetime(self):
        i = self._issued("reset_password")
        just_before = T0 + LIFETIME_S["reset_password"] - 1
        assert check_code(i.record, i.code, purpose="reset_password",
                          subject="7", now=just_before).ok
        at = T0 + LIFETIME_S["reset_password"]
        assert check_code(i.record, i.code, purpose="reset_password",
                          subject="7", now=at).outcome == "expired"

    def test_a_code_for_one_purpose_never_does_the_other(self):
        i = self._issued("verify_email")
        assert check_code(i.record, i.code, purpose="reset_password",
                          subject="7", now=T0).outcome == "wrong_purpose"

    def test_a_code_for_one_subject_never_does_another(self):
        i = self._issued(subject="7")
        assert check_code(i.record, i.code, purpose="verify_email",
                          subject="8", now=T0).outcome == "wrong_subject"

    def test_a_wrong_code_reveals_nothing_about_the_record(self):
        i = self._issued()
        used = check_code(i.record, i.code, purpose="verify_email",
                          subject="7", now=T0).record
        for rec in (i.record, used):
            for now in (T0, T0 + 10 * 86400):
                assert check_code(rec, "nope", purpose="reset_password",
                                  subject="8", now=now).outcome == "wrong_code"


class TestSender:

    def test_the_stand_in_keeps_what_it_would_send(self):
        s = get_email_sender("fake")
        assert isinstance(s, FakeEmailSender)
        s.send(address_check_email("owner@shop.example", "https://x/v?c=1"))
        assert [e.to for e in s.outbox] == ["owner@shop.example"]

    def test_no_other_service_exists(self):
        # Phase 329: "resend" exists, and needs its key (the resend tests).
        for name in ("smtp", "postmark", "", "Fake"):
            with pytest.raises(EmailNotConfigured):
                get_email_sender(name)

    def test_a_bad_address_is_refused(self):
        s = FakeEmailSender()
        for to in ("no-at-sign", " owner@shop.example", "owner@shop.example\n"):
            with pytest.raises(ValueError):
                s.send(Email(to, "s", "t"))
        assert s.outbox == []

    @pytest.mark.parametrize("make,hours", [(address_check_email, "24 hours"),
                                            (password_reset_email, "1 hour")])
    def test_each_email_carries_its_link_and_its_lifetime(self, make, hours):
        e = make("owner@shop.example", "https://api.example/link?c=abc")
        assert "https://api.example/link?c=abc" in e.text
        assert hours in e.text
        assert "ignore this email" in e.text

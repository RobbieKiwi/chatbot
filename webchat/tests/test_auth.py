from datetime import UTC, datetime, timedelta

from webchat.domain.auth import COOKIE_LIFETIME, cookie_valid, new_passphrase_record, passphrase_matches, sign_cookie

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def test_passphrase_matches_only_itself() -> None:
    record = new_passphrase_record(passphrase="correct horse")
    assert passphrase_matches(record=record, passphrase="correct horse")
    assert not passphrase_matches(record=record, passphrase="correct hors")


def test_records_for_the_same_passphrase_differ() -> None:
    first, second = new_passphrase_record(passphrase="same"), new_passphrase_record(passphrase="same")
    assert first.salt_hex != second.salt_hex
    assert first.cookie_secret_hex != second.cookie_secret_hex


def test_signed_cookie_is_valid_within_its_lifetime() -> None:
    record = new_passphrase_record(passphrase="p")
    cookie = sign_cookie(record=record, now=NOW)
    assert cookie_valid(record=record, cookie=cookie, now=NOW + COOKIE_LIFETIME - timedelta(minutes=1))


def test_expired_cookie_is_invalid() -> None:
    record = new_passphrase_record(passphrase="p")
    cookie = sign_cookie(record=record, now=NOW)
    assert not cookie_valid(record=record, cookie=cookie, now=NOW + COOKIE_LIFETIME + timedelta(minutes=1))


def test_tampered_cookie_is_invalid() -> None:
    record = new_passphrase_record(passphrase="p")
    issued, _, signature = sign_cookie(record=record, now=NOW).partition(".")
    assert not cookie_valid(record=record, cookie=f"{int(issued) + 1}.{signature}", now=NOW)


def test_cookie_from_other_secret_is_invalid() -> None:
    old, new = new_passphrase_record(passphrase="p"), new_passphrase_record(passphrase="p")
    assert not cookie_valid(record=new, cookie=sign_cookie(record=old, now=NOW), now=NOW)


def test_missing_or_garbage_cookie_is_invalid() -> None:
    record = new_passphrase_record(passphrase="p")
    for cookie in (None, "", "nonsense", "abc.def", "."):
        assert not cookie_valid(record=record, cookie=cookie, now=NOW)

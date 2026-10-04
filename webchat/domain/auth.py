"""Passphrase hashing and login-cookie signing. Pure: the caller supplies the record and the clock."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from webchat.models.config import PassphraseRecord

COOKIE_LIFETIME = timedelta(days=365)


def _scrypt(*, passphrase: str, salt: bytes) -> bytes:
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)


def new_passphrase_record(*, passphrase: str) -> PassphraseRecord:
    salt = secrets.token_bytes(nbytes=16)
    return PassphraseRecord(hash_hex=_scrypt(passphrase=passphrase, salt=salt).hex(), salt_hex=salt.hex(), cookie_secret_hex=secrets.token_hex(nbytes=32))


def passphrase_matches(*, record: PassphraseRecord, passphrase: str) -> bool:
    candidate = _scrypt(passphrase=passphrase, salt=bytes.fromhex(record.salt_hex))
    return hmac.compare_digest(candidate.hex(), record.hash_hex)


def _signature(*, record: PassphraseRecord, issued_s: int) -> str:
    return hmac.new(key=bytes.fromhex(record.cookie_secret_hex), msg=str(issued_s).encode("ascii"), digestmod=hashlib.sha256).hexdigest()


def sign_cookie(*, record: PassphraseRecord, now: datetime) -> str:
    issued_s = int(now.timestamp())
    return f"{issued_s}.{_signature(record=record, issued_s=issued_s)}"


def cookie_valid(*, record: PassphraseRecord, cookie: str | None, now: datetime) -> bool:
    issued_text, _, signature = (cookie or "").partition(".")
    if not issued_text.isdigit():
        return False
    issued_s = int(issued_text)
    if not hmac.compare_digest(signature, _signature(record=record, issued_s=issued_s)):
        return False
    return now - datetime.fromtimestamp(issued_s, tz=UTC) <= COOKIE_LIFETIME

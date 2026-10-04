"""Server settings and the passphrase, read from config.json."""

from pydantic import BaseModel, ConfigDict


class PassphraseRecord(BaseModel):
    hash_hex: str  # scrypt of the passphrase
    salt_hex: str
    cookie_secret_hex: str  # signs login cookies; replaced whenever the passphrase changes


class WebchatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    port: int = 8765
    passphrase: PassphraseRecord | None = None

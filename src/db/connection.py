import os

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()


def _read_key_bytes() -> bytes:
    """Local dev reads the key from a file (SNOWFLAKE_PRIVATE_KEY_PATH); a
    deployed container has no such file, so it instead reads the raw PEM text
    from SNOWFLAKE_PRIVATE_KEY_PEM (a GitHub Actions / Render secret)."""
    pem = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PEM")
    if pem:
        return pem.encode()
    with open(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"], "rb") as f:
        return f.read()


def _load_private_key():
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    p_key = serialization.load_pem_private_key(
        _read_key_bytes(),
        password=passphrase.encode() if passphrase else None,
        backend=default_backend(),
    )
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_snowflake_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=_load_private_key(),
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ.get("SNOWFLAKE_ROLE"),
    )

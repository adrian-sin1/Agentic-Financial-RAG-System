import os

import oci
from dotenv import load_dotenv

load_dotenv()


def _read_key() -> dict:
    """Local dev reads the private key from a file (OCI_PRIVATE_KEY_PATH); a
    deployed container has no such file, so it instead reads the raw PEM text
    from OCI_PRIVATE_KEY_PEM (a GitHub Actions / Render secret) -- same dual
    path as Snowflake's key handling in src/db/connection.py."""
    key_path = os.environ.get("OCI_PRIVATE_KEY_PATH")
    if key_path:
        return {"key_file": key_path}
    return {"key_content": os.environ["OCI_PRIVATE_KEY_PEM"]}


def get_client() -> oci.object_storage.ObjectStorageClient:
    config = {
        "user": os.environ["OCI_USER_OCID"],
        "tenancy": os.environ["OCI_TENANCY_OCID"],
        "fingerprint": os.environ["OCI_FINGERPRINT"],
        "region": os.environ["OCI_REGION"],
        **_read_key(),
    }
    passphrase = os.environ.get("OCI_PRIVATE_KEY_PASSPHRASE")
    if passphrase:
        config["pass_phrase"] = passphrase
    return oci.object_storage.ObjectStorageClient(config)


def get_from_bucket(object_path: str, local_dir: str) -> str:
    """Download a raw filing from the Oracle Cloud Object Storage bucket to
    local_dir, returning the local file path. object_path is the object name
    within the bucket, e.g. "apple/2025/aapl-20250927.htm".
    """
    os.makedirs(local_dir, exist_ok=True)
    response = get_client().get_object(os.environ["OCI_NAMESPACE"], os.environ["OCI_BUCKET_NAME"], object_path)

    filename = object_path.rsplit("/", 1)[-1]
    local_path = os.path.join(local_dir, filename)
    with open(local_path, "wb") as f:
        f.write(response.data.content)
    return local_path

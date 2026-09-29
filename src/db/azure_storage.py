import os

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()


def get_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(os.environ["AZURE_STORAGE_CONNECTION_STRING"])


def get_from_bucket(object_path: str, local_dir: str) -> str:
    """Download a raw filing from Azure Blob Storage to local_dir, returning
    the local file path. object_path is the blob name within the container,
    e.g. "apple/2025/aapl-20250927.htm". Named get_from_bucket() (not
    get_from_container()) to match the same interface src/db/oci_storage.py
    used, so callers didn't need to change when the storage backend did.
    """
    os.makedirs(local_dir, exist_ok=True)
    container_name = os.environ["AZURE_CONTAINER_NAME"]
    blob_client = get_client().get_blob_client(container=container_name, blob=object_path)

    filename = object_path.rsplit("/", 1)[-1]
    local_path = os.path.join(local_dir, filename)
    with open(local_path, "wb") as f:
        f.write(blob_client.download_blob().readall())
    return local_path

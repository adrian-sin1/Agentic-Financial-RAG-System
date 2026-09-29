"""One-time migration: copy every raw filing from the OCI Object Storage
bucket into the new Azure Blob Storage container, preserving the same
relative path (company/year/filename). Needed so re-ingestion/re-chunking
still works for documents ingested before the move off Oracle Cloud.

Run once from the project root: python scripts/migrate_raw_filings_to_azure.py
Safe to re-run -- upload_blob(overwrite=True) replaces, it doesn't duplicate.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.azure_storage import get_client as get_azure_client  # noqa: E402
from src.db.oci_storage import get_client as get_oci_client  # noqa: E402


def list_oci_objects() -> list[str]:
    oci_client = get_oci_client()
    namespace = os.environ["OCI_NAMESPACE"]
    bucket = os.environ["OCI_BUCKET_NAME"]
    response = oci_client.list_objects(namespace, bucket)
    return [obj.name for obj in response.data.objects]


def main():
    object_paths = list_oci_objects()
    print(f"Found {len(object_paths)} objects in the OCI bucket.")

    oci_client = get_oci_client()
    namespace = os.environ["OCI_NAMESPACE"]
    bucket = os.environ["OCI_BUCKET_NAME"]

    azure_client = get_azure_client()
    container_name = os.environ["AZURE_CONTAINER_NAME"]

    for object_path in object_paths:
        response = oci_client.get_object(namespace, bucket, object_path)
        blob_client = azure_client.get_blob_client(container=container_name, blob=object_path)
        blob_client.upload_blob(response.data.content, overwrite=True)
        print(f"Migrated {object_path}")

    print("Done. Verify the blobs in the Azure portal before decommissioning the OCI bucket.")


if __name__ == "__main__":
    main()

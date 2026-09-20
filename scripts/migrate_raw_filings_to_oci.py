"""One-time migration: copy every raw filing already sitting in Snowflake's
internal stage (FINANCIAL_RAG.RAW.RAW_FILINGS) into the new OCI Object
Storage bucket, preserving the same relative path (company/year/filename).
Needed so re-ingestion/re-chunking still works for documents ingested before
the move off Snowflake's stage -- otherwise their original HTML would be
stranded in the old stage with nothing left pointing at it.

Run once from the project root: python scripts/migrate_raw_filings_to_oci.py
Safe to re-run -- put_object overwrites, it doesn't duplicate.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.connection import get_snowflake_connection  # noqa: E402
from src.db.oci_storage import get_client  # noqa: E402

# The stage this one-time migration reads from. Inlined here (rather than
# imported from a src/db/stage.py module) since that module no longer exists
# in the live app -- raw file storage moved to OCI. Kept self-contained so
# this script stays a runnable historical record of the migration.
RAW_STAGE = "FINANCIAL_RAG.RAW.RAW_FILINGS"
STAGE_PREFIX = "raw_filings/"


def list_stage_objects() -> list[str]:
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute(f"LIST @{RAW_STAGE}")
    rows = cur.fetchall()
    conn.close()
    # Snowflake prefixes each listed path with the stage's own directory name
    # (e.g. "raw_filings/apple/2025/aapl-20250927.htm") -- strip that off to
    # get the relative object_path the app actually uses.
    return [row[0][len(STAGE_PREFIX) :] for row in rows if row[0].startswith(STAGE_PREFIX)]


def get_from_stage(stage_relative_path: str, local_dir: str) -> str:
    os.makedirs(local_dir, exist_ok=True)
    abs_dir = os.path.abspath(local_dir).replace("\\", "/")
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute(f"GET @{RAW_STAGE}/{stage_relative_path} 'file://{abs_dir}'")
    conn.close()
    filename = stage_relative_path.rsplit("/", 1)[-1]
    return os.path.join(local_dir, filename)


def main():
    object_paths = list_stage_objects()
    print(f"Found {len(object_paths)} objects in the Snowflake stage.")

    client = get_client()
    namespace = os.environ["OCI_NAMESPACE"]
    bucket = os.environ["OCI_BUCKET_NAME"]

    for object_path in object_paths:
        local_path = get_from_stage(object_path, "data/raw/_migration_tmp")
        with open(local_path, "rb") as f:
            client.put_object(namespace, bucket, object_path, f)
        os.remove(local_path)
        print(f"Migrated {object_path}")

    print("Done. Verify the objects in the OCI console, then re-run ingestion checks before removing the old stage.")


if __name__ == "__main__":
    main()

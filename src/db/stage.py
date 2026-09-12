import os

from src.db.connection import get_snowflake_connection

RAW_STAGE = "FINANCIAL_RAG.RAW.RAW_FILINGS"


def get_from_stage(stage_relative_path: str, local_dir: str) -> str:
    """Download a file from the raw filings stage to local_dir, returning the
    local file path. stage_relative_path is the path under the stage, e.g.
    "apple/2025/aapl-20250927.htm".
    """
    os.makedirs(local_dir, exist_ok=True)
    abs_dir = os.path.abspath(local_dir).replace("\\", "/")
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute(f"GET @{RAW_STAGE}/{stage_relative_path} 'file://{abs_dir}'")
    conn.close()
    filename = stage_relative_path.rsplit("/", 1)[-1]
    return os.path.join(local_dir, filename)

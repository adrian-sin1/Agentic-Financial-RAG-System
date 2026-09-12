CREATE TABLE IF NOT EXISTS documents (
    document_id     STRING PRIMARY KEY,
    company         STRING NOT NULL,
    year            NUMBER NOT NULL,
    document_type   STRING,
    source_filename STRING,
    ingested_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id     STRING PRIMARY KEY,
    document_id  STRING NOT NULL,
    company      STRING NOT NULL,
    year         NUMBER NOT NULL,
    document_type STRING,
    section      STRING,
    page         NUMBER,
    chunk_text   STRING NOT NULL,
    created_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    metric_id     STRING PRIMARY KEY,
    company       STRING NOT NULL,
    year          NUMBER NOT NULL,
    fiscal_period STRING,
    metric_name   STRING NOT NULL,
    metric_value  FLOAT,
    unit          STRING,
    source        STRING,
    created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS query_log (
    query_id    STRING PRIMARY KEY,
    question    STRING NOT NULL,
    tool_calls  VARIANT,
    answer      STRING,
    latency_ms  NUMBER,
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

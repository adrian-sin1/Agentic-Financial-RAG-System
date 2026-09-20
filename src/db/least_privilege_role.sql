-- Replaces financial_rag_svc's blanket SYSADMIN role with a narrowly-scoped
-- custom role that only has the privileges the app code actually uses.
-- Run once in Snowsight as ACCOUNTADMIN (select all, "Run All").
--
-- NOTE: as originally run, this also granted READ on the FINANCIAL_RAG.RAW.
-- RAW_FILINGS stage and USAGE on the RAW schema, for the raw-filing download
-- step. That step has since moved to Oracle Cloud Object Storage (see
-- src/db/oci_storage.py and src/db/migrations/002_revoke_unused_stage_access.sql),
-- so a fresh setup following this file today doesn't need either grant.

USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS FINANCIAL_RAG_APP_ROLE;

GRANT USAGE ON DATABASE FINANCIAL_RAG TO ROLE FINANCIAL_RAG_APP_ROLE;
GRANT USAGE ON SCHEMA FINANCIAL_RAG.PUBLIC TO ROLE FINANCIAL_RAG_APP_ROLE;

-- Row-level CRUD only -- no CREATE/ALTER/DROP, no OWNERSHIP. Schema changes
-- (e.g. adding columns) are done by an admin, not the app's own credentials.
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE FINANCIAL_RAG.PUBLIC.DOCUMENTS TO ROLE FINANCIAL_RAG_APP_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE FINANCIAL_RAG.PUBLIC.DOCUMENT_CHUNKS TO ROLE FINANCIAL_RAG_APP_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE FINANCIAL_RAG.PUBLIC.FINANCIAL_METRICS TO ROLE FINANCIAL_RAG_APP_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE FINANCIAL_RAG.PUBLIC.QUERY_LOG TO ROLE FINANCIAL_RAG_APP_ROLE;

-- Any future table added to PUBLIC gets the same grants automatically, so this
-- role doesn't silently lose access after the next schema.sql change.
GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA FINANCIAL_RAG.PUBLIC TO ROLE FINANCIAL_RAG_APP_ROLE;

GRANT USAGE ON WAREHOUSE FINANCIAL_RAG_WH TO ROLE FINANCIAL_RAG_APP_ROLE;

GRANT ROLE FINANCIAL_RAG_APP_ROLE TO USER financial_rag_svc;
ALTER USER financial_rag_svc SET DEFAULT_ROLE = FINANCIAL_RAG_APP_ROLE;

-- Drop the blanket SYSADMIN grant now that the scoped role covers everything
-- the service account needs.
REVOKE ROLE SYSADMIN FROM USER financial_rag_svc;

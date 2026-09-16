-- Adds richer observability to query_log: which chunks were actually
-- retrieved and which SQL parameters were actually used per request, not
-- just that hybrid_search/sql_tool were called. Run once in Snowsight as
-- ACCOUNTADMIN -- FINANCIAL_RAG_APP_ROLE intentionally has no ALTER/OWNERSHIP
-- privilege on this table (see src/db/least_privilege_role.sql), so schema
-- changes stay an admin-only action.

USE ROLE ACCOUNTADMIN;

ALTER TABLE FINANCIAL_RAG.PUBLIC.QUERY_LOG ADD COLUMN IF NOT EXISTS documents_retrieved VARIANT;
ALTER TABLE FINANCIAL_RAG.PUBLIC.QUERY_LOG ADD COLUMN IF NOT EXISTS sql_queries_used VARIANT;

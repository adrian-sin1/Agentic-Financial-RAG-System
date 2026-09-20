-- Raw filing storage moved from Snowflake's internal stage to Oracle Cloud
-- Object Storage (see src/db/oci_storage.py). Run this ONLY after
-- scripts/migrate_raw_filings_to_oci.py has completed successfully and a
-- test ingestion against the new OCI bucket has been verified -- it removes
-- the app role's access to the old stage, so don't run it while the old
-- stage is still the active raw-file source. Run in Snowsight as ACCOUNTADMIN.

USE ROLE ACCOUNTADMIN;

REVOKE READ ON STAGE FINANCIAL_RAG.RAW.RAW_FILINGS FROM ROLE FINANCIAL_RAG_APP_ROLE;
REVOKE USAGE ON SCHEMA FINANCIAL_RAG.RAW FROM ROLE FINANCIAL_RAG_APP_ROLE;

-- The stage itself (and its files) is left in place as a dormant backup --
-- not dropped, in case anything about the OCI migration needs to be
-- cross-checked later. Drop it manually once you're confident it's unneeded:
--   DROP STAGE FINANCIAL_RAG.RAW.RAW_FILINGS;

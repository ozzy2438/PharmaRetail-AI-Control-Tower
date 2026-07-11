-- RAW landing tables for the processed UCI + seed datasets (Data Ingestion phase).
-- PHARMARETAIL_ADMIN already owns the RAW schema (03_database_schemas.sql), so this
-- runs as BAU like 04_grants.sql/06_validation.sql; no ACCOUNTADMIN bootstrap needed.
USE ROLE PHARMARETAIL_ADMIN;
ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_RAW_INGESTION_DDL';

-- Internal stage used by scripts/load_raw_data.py to PUT local files before COPY INTO.
CREATE STAGE IF NOT EXISTS PHARMARETAIL_AI_CONTROL_TOWER.RAW.RAW_LOAD_STAGE
    COMMENT = 'Internal stage for loading processed local datasets into RAW landing tables';

-- Audit trail for every load attempt, successful or failed. One row per dataset per run.
CREATE TABLE IF NOT EXISTS PHARMARETAIL_AI_CONTROL_TOWER.RAW.LOAD_AUDIT (
    LOAD_ID STRING NOT NULL,
    TABLE_NAME STRING NOT NULL,
    SOURCE_FILE STRING NOT NULL,
    FILE_SHA256 STRING NOT NULL,
    SOURCE_ROW_COUNT NUMBER NOT NULL,
    LOADED_ROW_COUNT NUMBER,
    ROW_COUNT_MATCH BOOLEAN,
    NULL_COUNTS VARIANT,
    DUPLICATE_ROW_COUNT NUMBER NOT NULL,
    LOAD_STATUS STRING NOT NULL,
    ERROR_MESSAGE STRING,
    STARTED_AT TIMESTAMP_NTZ NOT NULL,
    COMPLETED_AT TIMESTAMP_NTZ
)
COMMENT = 'Load audit trail: row counts, null summary, duplicates, checksum and status per load run';

-- Deduplicated, valid-price, non-return UCI Online Retail invoice lines. See contracts/uci_sales.yml.
CREATE TABLE IF NOT EXISTS PHARMARETAIL_AI_CONTROL_TOWER.RAW.UCI_SALES (
    INVOICE STRING NOT NULL,
    STOCK_CODE STRING NOT NULL,
    DESCRIPTION STRING,
    QUANTITY NUMBER NOT NULL,
    INVOICE_DATE TIMESTAMP_NTZ NOT NULL,
    PRICE FLOAT NOT NULL,
    CUSTOMER_ID STRING,
    COUNTRY STRING NOT NULL,
    IS_CUSTOMER_IDENTIFIED BOOLEAN NOT NULL,
    _LOAD_ID STRING NOT NULL,
    _LOADED_AT TIMESTAMP_NTZ NOT NULL,
    _SOURCE_FILE STRING NOT NULL
)
COMMENT = 'Landing zone for data/processed/uci_sales_clean.parquet; see contracts/uci_sales.yml';

-- Deduplicated, valid-price UCI Online Retail invoice lines classified as returns. See contracts/uci_returns.yml.
CREATE TABLE IF NOT EXISTS PHARMARETAIL_AI_CONTROL_TOWER.RAW.UCI_RETURNS (
    INVOICE STRING NOT NULL,
    STOCK_CODE STRING NOT NULL,
    DESCRIPTION STRING,
    QUANTITY NUMBER NOT NULL,
    INVOICE_DATE TIMESTAMP_NTZ NOT NULL,
    PRICE FLOAT NOT NULL,
    CUSTOMER_ID STRING,
    COUNTRY STRING NOT NULL,
    IS_CUSTOMER_IDENTIFIED BOOLEAN NOT NULL,
    _LOAD_ID STRING NOT NULL,
    _LOADED_AT TIMESTAMP_NTZ NOT NULL,
    _SOURCE_FILE STRING NOT NULL
)
COMMENT = 'Landing zone for data/processed/uci_returns_clean.parquet; see contracts/uci_returns.yml';

-- Quarantined non-positive-price rows, kept separate from sales/returns. See contracts/uci_invalid_price.yml.
CREATE TABLE IF NOT EXISTS PHARMARETAIL_AI_CONTROL_TOWER.RAW.UCI_SALES_QUARANTINE (
    INVOICE STRING NOT NULL,
    STOCK_CODE STRING NOT NULL,
    DESCRIPTION STRING,
    QUANTITY NUMBER NOT NULL,
    INVOICE_DATE TIMESTAMP_NTZ NOT NULL,
    PRICE FLOAT NOT NULL,
    CUSTOMER_ID STRING,
    COUNTRY STRING NOT NULL,
    IS_CUSTOMER_IDENTIFIED BOOLEAN NOT NULL,
    QUARANTINE_REASON STRING NOT NULL,
    _LOAD_ID STRING NOT NULL,
    _LOADED_AT TIMESTAMP_NTZ NOT NULL,
    _SOURCE_FILE STRING NOT NULL
)
COMMENT = 'Landing zone for data/quarantine/uci_invalid_price.parquet; never blended into sales/returns';

-- Store dimension seed. See contracts/dim_store.yml.
CREATE TABLE IF NOT EXISTS PHARMARETAIL_AI_CONTROL_TOWER.RAW.DIM_STORE_SEED (
    STORE_ID STRING NOT NULL,
    STORE_NAME STRING NOT NULL,
    STATE STRING NOT NULL,
    POSTCODE STRING,
    LATITUDE FLOAT NOT NULL,
    LONGITUDE FLOAT NOT NULL,
    REGION STRING NOT NULL,
    _LOAD_ID STRING NOT NULL,
    _LOADED_AT TIMESTAMP_NTZ NOT NULL,
    _SOURCE_FILE STRING NOT NULL
)
COMMENT = 'Landing zone for data/processed/dim_store_seed.csv; see contracts/dim_store.yml';

-- Product dimension seed. See contracts/dim_product.yml.
CREATE TABLE IF NOT EXISTS PHARMARETAIL_AI_CONTROL_TOWER.RAW.DIM_PRODUCT_SEED (
    PRODUCT_ID STRING NOT NULL,
    PRODUCT_NAME STRING NOT NULL,
    BRAND STRING NOT NULL,
    CATEGORY STRING NOT NULL,
    PACK_SIZE STRING NOT NULL,
    COLD_CHAIN_FLAG NUMBER NOT NULL,
    REGULATED_PRODUCT_FLAG NUMBER NOT NULL,
    _LOAD_ID STRING NOT NULL,
    _LOADED_AT TIMESTAMP_NTZ NOT NULL,
    _SOURCE_FILE STRING NOT NULL
)
COMMENT = 'Landing zone for data/processed/dim_product_seed.csv; see contracts/dim_product.yml';

-- Bootstrap-only service identity for the Phase 6 Stockout Investigation Agent.
-- Run with ACCOUNTADMIN through the human-gated bootstrap deploy path. This
-- identity is deliberately separate from the human bootstrap user (OMRUM), the
-- foundation CI/CD identity (SVC_PHARMARETAIL_CICD) and the dbt identity
-- (SVC_PHARMARETAIL_DBT).
--
-- It is granted PHARMARETAIL_AI_APP ONLY, whose privileges are already defined
-- elsewhere: SELECT on the approved MARTS models (phase4_model_grants.sql),
-- INSERT on AI_LOGS agent tables (12_phase6_agent.sql) and INSERT on the
-- operational audit (10_phase4_governance.sql). No UPDATE/DELETE, no ADMIN,
-- no ACCOUNTADMIN is ever granted here.
--
-- BEFORE DEPLOY: generate an RSA key-pair, keep the private key OUT of this
-- repository (store it as a GitHub Environment secret), and paste the matching
-- PUBLIC key (non-secret) below in place of the placeholder. The placeholder
-- below is intentionally not a valid key, so an accidental deploy fails safely
-- until a real public key is provided.
-- noqa: disable=CP02,LT02,LT09,PRS
USE ROLE ACCOUNTADMIN;
ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_PHASE6_AI_APP_IDENTITY';

CREATE USER IF NOT EXISTS SVC_PHARMARETAIL_AI_APP
    TYPE = SERVICE
    RSA_PUBLIC_KEY = 'REPLACE_WITH_AI_APP_RSA_PUBLIC_KEY'
    DEFAULT_ROLE = PHARMARETAIL_AI_APP
    DEFAULT_WAREHOUSE = WH_PHARMARETAIL
    DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
    COMMENT = 'Phase 6 agent identity; key-pair auth, PHARMARETAIL_AI_APP scope only';

-- Reconcile the public key on repeat runs (rotation) without dropping the user.
ALTER USER IF EXISTS SVC_PHARMARETAIL_AI_APP SET
RSA_PUBLIC_KEY = 'REPLACE_WITH_AI_APP_RSA_PUBLIC_KEY'
DEFAULT_ROLE = PHARMARETAIL_AI_APP
DEFAULT_WAREHOUSE = WH_PHARMARETAIL
DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
COMMENT = 'Phase 6 agent identity; key-pair auth, PHARMARETAIL_AI_APP scope only';

-- The agent identity may only ever hold PHARMARETAIL_AI_APP. Verify drift with
-- `SHOW GRANTS TO USER SVC_PHARMARETAIL_AI_APP`.
GRANT ROLE PHARMARETAIL_AI_APP TO USER SVC_PHARMARETAIL_AI_APP;

-- MANUAL, DESTRUCTIVE, AND INTENTIONALLY NOT EXECUTED BY AUTOMATION.
--
-- Preconditions:
-- 1. Open and approve an incident/change issue and production pull request.
-- 2. Export or confirm disposal of every project object and audit record.
-- 3. Confirm there are no active dbt, AI application, or user sessions.
-- 4. Run 06_validation.sql and capture evidence before rollback.
-- 5. Use ACCOUNTADMIN only for the approved teardown window.
--
-- Commands remain commented to prevent accidental execution. Uncomment one
-- checkpoint at a time, validate its effect, and stop immediately on variance.

-- USE ROLE ACCOUNTADMIN;
-- ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_FOUNDATION_APPROVED_ROLLBACK';

-- Checkpoint 1: stop project compute and detach the cost monitor.
-- ALTER WAREHOUSE IF EXISTS WH_PHARMARETAIL SUSPEND;
-- ALTER WAREHOUSE IF EXISTS WH_PHARMARETAIL UNSET RESOURCE_MONITOR;

-- Checkpoint 2: remove the dedicated data boundary.
-- WARNING: this irreversibly removes all project tables, views, logs and metadata.
-- DROP DATABASE IF EXISTS PHARMARETAIL_AI_CONTROL_TOWER;

-- Checkpoint 3: remove compute and the now-unassigned monitor.
-- DROP WAREHOUSE IF EXISTS WH_PHARMARETAIL;
-- DROP RESOURCE MONITOR IF EXISTS RM_PHARMARETAIL_MONTHLY;

-- Checkpoint 4: detach role hierarchy before removing roles.
-- REVOKE ROLE PHARMARETAIL_ADMIN FROM USER OMRUM;
-- REVOKE ROLE PHARMARETAIL_ADMIN FROM ROLE SYSADMIN;
-- REVOKE ROLE PHARMARETAIL_ENGINEER FROM ROLE PHARMARETAIL_ADMIN;
-- REVOKE ROLE PHARMARETAIL_DBT FROM ROLE PHARMARETAIL_ADMIN;
-- REVOKE ROLE PHARMARETAIL_AI_APP FROM ROLE PHARMARETAIL_ADMIN;
-- REVOKE ROLE PHARMARETAIL_READONLY FROM ROLE PHARMARETAIL_ADMIN;

-- Checkpoint 5: remove child roles, then the parent role.
-- DROP ROLE IF EXISTS PHARMARETAIL_ENGINEER;
-- DROP ROLE IF EXISTS PHARMARETAIL_DBT;
-- DROP ROLE IF EXISTS PHARMARETAIL_AI_APP;
-- DROP ROLE IF EXISTS PHARMARETAIL_READONLY;
-- DROP ROLE IF EXISTS PHARMARETAIL_ADMIN;

-- Postcondition: SHOW objects/roles and attach evidence to the rollback issue.

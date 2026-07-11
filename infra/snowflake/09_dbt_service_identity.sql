-- Bootstrap-only service identity for dbt transformations. Run with ACCOUNTADMIN.
-- Separates dbt job automation from both the human bootstrap user (OMRUM) and
-- the foundation CI/CD identity (SVC_PHARMARETAIL_CICD, PHARMARETAIL_ADMIN).
USE ROLE ACCOUNTADMIN;
ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_FOUNDATION_DBT_IDENTITY';

-- TYPE = SERVICE disallows password/MFA and interactive login entirely; the
-- account can only authenticate with an RSA private key matching the public
-- key below. The RSA_PUBLIC_KEY value is non-secret and safe to commit; the
-- matching private key itself is held outside this repository.
CREATE USER IF NOT EXISTS SVC_PHARMARETAIL_DBT
    TYPE = SERVICE
    RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAo7Q8cKu1ub8zpKCNOqtyntKiaMptmCHn5QSYfnZ6kHQEZXgLQWv/5xTEq3nYeKs5g12xJ474693Vrm9CmtfOMOrIZ7Jnedc2SWOEbaslYzMYFjgBv/OGvqhF6vN7iAj78Obu7JM0NVa/4JfJb37fLeSyCzQo3w6oqyE4Z4XVPH3EBsIZWkrtLysEj6BOTOfzPzAKWdryJ9NsRqLQDZYAmbJpJrXsw3Z/UC+geWH/6b4Y+6P3qXdEYRdCM8unPZRHk46wfpboXyf3b1CpeiHmCfD137eI3QNrCZ0ZxB82JgQQBp1xyYsYj1OOwlSsZwMzAA8M3UWqP2CiAFSc/GAsBQIDAQAB' -- noqa: LT05
    DEFAULT_ROLE = PHARMARETAIL_DBT
    DEFAULT_WAREHOUSE = WH_PHARMARETAIL
    DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
    COMMENT = 'dbt transformation identity for PharmaRetail AI Control Tower; key-pair auth, PHARMARETAIL_DBT scope';

-- Reconcile the public key on repeat runs (rotation) without dropping the user.
ALTER USER IF EXISTS SVC_PHARMARETAIL_DBT SET
RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAo7Q8cKu1ub8zpKCNOqtyntKiaMptmCHn5QSYfnZ6kHQEZXgLQWv/5xTEq3nYeKs5g12xJ474693Vrm9CmtfOMOrIZ7Jnedc2SWOEbaslYzMYFjgBv/OGvqhF6vN7iAj78Obu7JM0NVa/4JfJb37fLeSyCzQo3w6oqyE4Z4XVPH3EBsIZWkrtLysEj6BOTOfzPzAKWdryJ9NsRqLQDZYAmbJpJrXsw3Z/UC+geWH/6b4Y+6P3qXdEYRdCM8unPZRHk46wfpboXyf3b1CpeiHmCfD137eI3QNrCZ0ZxB82JgQQBp1xyYsYj1OOwlSsZwMzAA8M3UWqP2CiAFSc/GAsBQIDAQAB' -- noqa: LT05
DEFAULT_ROLE = PHARMARETAIL_DBT
DEFAULT_WAREHOUSE = WH_PHARMARETAIL
DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
COMMENT = 'dbt transformation identity for PharmaRetail AI Control Tower; key-pair auth, PHARMARETAIL_DBT scope';

-- This script only ever grants PHARMARETAIL_DBT; it does not revoke other
-- roles, so it cannot itself remediate an out-of-band grant (e.g. ADMIN
-- assigned manually outside this script). Verify with
-- `SHOW GRANTS TO USER SVC_PHARMARETAIL_DBT` if drift is suspected, per the
-- runbook's BAU checklist. No ADMIN or ACCOUNTADMIN should ever be granted
-- here: this identity is intended to read RAW and read/write STAGING,
-- INTERMEDIATE and MARTS only (see docs/snowflake_security_matrix.md).
GRANT ROLE PHARMARETAIL_DBT TO USER SVC_PHARMARETAIL_DBT;

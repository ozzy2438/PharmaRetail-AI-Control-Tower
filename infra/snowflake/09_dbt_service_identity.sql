-- Bootstrap-only service identity for dbt transformations. Run with ACCOUNTADMIN.
-- Separates dbt job automation from both the human bootstrap user (OMRUM) and
-- the foundation CI/CD identity (SVC_PHARMARETAIL_CICD, PHARMARETAIL_ADMIN).
USE ROLE ACCOUNTADMIN;
ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_FOUNDATION_DBT_IDENTITY';

-- TYPE = SERVICE disallows password/MFA and interactive login entirely; the
-- account can only authenticate with the matching RSA private key below.
-- The RSA_PUBLIC_KEY value is non-secret and safe to commit; only the
-- matching private key (held outside this repository) can authenticate.
CREATE USER IF NOT EXISTS SVC_PHARMARETAIL_DBT
    TYPE = SERVICE
    RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsynnRFRcrUgv/WTfIyWYRXAdzuEvDj0iGlh2I+SoLbRpcsNk9ynffKbKvHpV5kYW9H4R/42KHSucrb5FOKXexe0QHjLSMdox2g5mc+ObFkzzx1fZKQr+ybow1wrp3W91jNNaKeWz0lFQda8UUircICwNgGeYB+meAUbmUX/6lfLYurnA08/Tl24cn1QbcIgkmt+YnWbK6mbU4XrWEfXJHsy1T3GfVNIivooWWjNLWmF1JqTY4HSeowN+dueKpMVOaLjJdAE/0th3NdCXF7gdk3AD38dcX6d4ToNXKZVjkMgiVzDGEdLF54EsonXWenj59hz6SlTQ3+mudsU9cCHeOQIDAQAB' -- noqa: LT05
    DEFAULT_ROLE = PHARMARETAIL_DBT
    DEFAULT_WAREHOUSE = WH_PHARMARETAIL
    DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
    COMMENT = 'dbt transformation identity for PharmaRetail AI Control Tower; key-pair auth, PHARMARETAIL_DBT scope';

-- Reconcile the public key on repeat runs (rotation) without dropping the user.
ALTER USER IF EXISTS SVC_PHARMARETAIL_DBT SET
RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsynnRFRcrUgv/WTfIyWYRXAdzuEvDj0iGlh2I+SoLbRpcsNk9ynffKbKvHpV5kYW9H4R/42KHSucrb5FOKXexe0QHjLSMdox2g5mc+ObFkzzx1fZKQr+ybow1wrp3W91jNNaKeWz0lFQda8UUircICwNgGeYB+meAUbmUX/6lfLYurnA08/Tl24cn1QbcIgkmt+YnWbK6mbU4XrWEfXJHsy1T3GfVNIivooWWjNLWmF1JqTY4HSeowN+dueKpMVOaLjJdAE/0th3NdCXF7gdk3AD38dcX6d4ToNXKZVjkMgiVzDGEdLF54EsonXWenj59hz6SlTQ3+mudsU9cCHeOQIDAQAB' -- noqa: LT05
DEFAULT_ROLE = PHARMARETAIL_DBT
DEFAULT_WAREHOUSE = WH_PHARMARETAIL
DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
COMMENT = 'dbt transformation identity for PharmaRetail AI Control Tower; key-pair auth, PHARMARETAIL_DBT scope';

-- Grant only the existing PHARMARETAIL_DBT role. No ADMIN, no ACCOUNTADMIN.
-- This identity can read RAW and read/write STAGING, INTERMEDIATE and MARTS,
-- and nothing else (see docs/snowflake_security_matrix.md).
GRANT ROLE PHARMARETAIL_DBT TO USER SVC_PHARMARETAIL_DBT;

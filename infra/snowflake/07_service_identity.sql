-- Bootstrap-only service identity for CI/CD automation. Run with ACCOUNTADMIN.
-- Separates BAU deployment automation from the human bootstrap user (OMRUM).
USE ROLE ACCOUNTADMIN;
ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_FOUNDATION_SERVICE_IDENTITY';

-- TYPE = SERVICE disallows password/MFA and interactive login entirely; the
-- account can only authenticate with the matching RSA private key below.
-- The RSA_PUBLIC_KEY value is non-secret and safe to commit; only the
-- matching private key (held outside this repository) can authenticate.
CREATE USER IF NOT EXISTS SVC_PHARMARETAIL_CICD
    TYPE = SERVICE
    RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwKfIFYEcaaoVPSsnIIkJ92dKBM5BN7xuplgOh06Z3gTb/Jt8Zpbfrj5wKB9eIsUwSad3kFBFsQvQHA2lroZNGocpAdRcZ4fTomS2muxTXsIlm7VIn55o0PT69UqK4LvDhIQdWRxWVb/ykbdeaYwcN2XhoKZO+NQZBF9Xkl+nvtdsS1cj54sx2/0VUxb7iiBvXNEShLnJDdo2xz1PGdg4GFaWm/NHyPbdxYZc+A4bmzLsra/KlU2UAoCRLHfehtM80Bq5qiFXOmp++I9sZC2iUjpmHSZWCkzk57xcxCMtcZYszVkrH2sT61aWHe08A7PyIdEihoPNmVDU1rsVX/q0ZwIDAQAB' -- noqa: LT05
    DEFAULT_ROLE = PHARMARETAIL_ADMIN
    DEFAULT_WAREHOUSE = WH_PHARMARETAIL
    DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
    COMMENT = 'CI/CD service identity for PharmaRetail AI Control Tower BAU deployments; key-pair auth only';

-- Reconcile the public key on repeat runs (rotation) without dropping the user.
ALTER USER IF EXISTS SVC_PHARMARETAIL_CICD SET
RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwKfIFYEcaaoVPSsnIIkJ92dKBM5BN7xuplgOh06Z3gTb/Jt8Zpbfrj5wKB9eIsUwSad3kFBFsQvQHA2lroZNGocpAdRcZ4fTomS2muxTXsIlm7VIn55o0PT69UqK4LvDhIQdWRxWVb/ykbdeaYwcN2XhoKZO+NQZBF9Xkl+nvtdsS1cj54sx2/0VUxb7iiBvXNEShLnJDdo2xz1PGdg4GFaWm/NHyPbdxYZc+A4bmzLsra/KlU2UAoCRLHfehtM80Bq5qiFXOmp++I9sZC2iUjpmHSZWCkzk57xcxCMtcZYszVkrH2sT61aWHe08A7PyIdEihoPNmVDU1rsVX/q0ZwIDAQAB' -- noqa: LT05
DEFAULT_ROLE = PHARMARETAIL_ADMIN
DEFAULT_WAREHOUSE = WH_PHARMARETAIL
DEFAULT_NAMESPACE = PHARMARETAIL_AI_CONTROL_TOWER
COMMENT = 'CI/CD service identity for PharmaRetail AI Control Tower BAU deployments; key-pair auth only';

-- Grant only the existing PHARMARETAIL_ADMIN role. This is the same role BAU
-- deployments already use; the change is identity separation, not scope.
GRANT ROLE PHARMARETAIL_ADMIN TO USER SVC_PHARMARETAIL_CICD;

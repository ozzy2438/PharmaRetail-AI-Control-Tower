from __future__ import annotations

import pytest

from scripts.validate_phase4_determinism import connection_kwargs
from scripts.validate_phase4_governance import ACTIVE_DBT_KEY_FP


def test_determinism_connection_uses_dbt_service_role() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    kwargs = connection_kwargs(
        {
            "SNOWFLAKE_ACCOUNT": "ORG-ACCOUNT",
            "SNOWFLAKE_DBT_USER": "SVC_PHARMARETAIL_DBT",
            "SNOWFLAKE_PRIVATE_KEY": pem,
            "SNOWFLAKE_DATABASE": "PHARMARETAIL_AI_CONTROL_TOWER",
            "SNOWFLAKE_WAREHOUSE": "WH_PHARMARETAIL",
        }
    )
    assert kwargs["role"] == "PHARMARETAIL_DBT"
    assert kwargs["user"] == "SVC_PHARMARETAIL_DBT"
    assert "private_key" in kwargs


def test_determinism_connection_reports_missing_names_without_values() -> None:
    with pytest.raises(ValueError, match="SNOWFLAKE_DBT_USER"):
        connection_kwargs({})


def test_active_key_fingerprint_is_a_non_secret_sha256_value() -> None:
    assert ACTIVE_DBT_KEY_FP.startswith("SHA256:")
    assert len(ACTIVE_DBT_KEY_FP) == 51

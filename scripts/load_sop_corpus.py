"""Idempotently load the committed SOP corpus into Snowflake GOVERNANCE."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.deploy_snowflake import load_private_key_der
from scripts.rag_corpus import EMBEDDING_DIMENSION, EMBEDDING_MODEL, load_corpus
from scripts.validate_snowflake_config import SnowflakeConfig

DATABASE = "PHARMARETAIL_AI_CONTROL_TOWER"
SCHEMA = f"{DATABASE}.GOVERNANCE"


def connect(config: SnowflakeConfig):  # noqa: ANN201
    import snowflake.connector

    kwargs: dict[str, object] = {
        "account": config.account,
        "user": config.user,
        "role": config.role,
        "warehouse": config.warehouse,
        "database": config.database,
        "session_parameters": {"QUERY_TAG": "PHARMARETAIL_PHASE5_SOP_INGEST"},
    }
    if config.private_key_pem:
        kwargs["private_key"] = load_private_key_der(
            config.private_key_pem, config.private_key_passphrase
        )
    else:
        kwargs["password"] = config.password
    return snowflake.connector.connect(**kwargs)


def load(connection, corpus_root: Path) -> tuple[int, int]:  # noqa: ANN001
    documents, chunks = load_corpus(corpus_root)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cursor = connection.cursor()
    try:
        cursor.execute("ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_PHASE5_SOP_INGEST'")
        for document in documents:
            cursor.execute(
                f"""
                MERGE INTO {SCHEMA}.DOCUMENT_REGISTRY AS target
                USING (SELECT %s DOC_ID, %s VERSION) AS source
                ON target.DOC_ID = source.DOC_ID AND target.VERSION = source.VERSION
                WHEN MATCHED THEN UPDATE SET
                    TITLE = %s, EFFECTIVE_DATE = %s, EXPIRY_DATE = %s, COUNTRY = %s,
                    BUSINESS_UNIT = %s, POLICY_OWNER = %s, ACCESS_LEVEL = %s,
                    SECTION_ID = %s, SOURCE_TYPE = %s, SOURCE_FILE = %s,
                    CONTENT_HASH = %s, DOCUMENT_STATUS = 'ACTIVE', INGESTED_AT = %s
                WHEN NOT MATCHED THEN INSERT (
                    DOC_ID, TITLE, VERSION, EFFECTIVE_DATE, EXPIRY_DATE, COUNTRY,
                    BUSINESS_UNIT, POLICY_OWNER, ACCESS_LEVEL, SECTION_ID, SOURCE_TYPE,
                    SOURCE_FILE, CONTENT_HASH, DOCUMENT_STATUS, INGESTED_AT
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s)
                """,
                (
                    document.doc_id,
                    document.version,
                    document.title,
                    document.effective_date,
                    document.expiry_date,
                    document.country,
                    document.business_unit,
                    document.policy_owner,
                    document.access_level,
                    document.section_id,
                    document.source_type,
                    document.source_file,
                    document.content_hash,
                    now,
                    document.doc_id,
                    document.title,
                    document.version,
                    document.effective_date,
                    document.expiry_date,
                    document.country,
                    document.business_unit,
                    document.policy_owner,
                    document.access_level,
                    document.section_id,
                    document.source_type,
                    document.source_file,
                    document.content_hash,
                    now,
                ),
            )
            cursor.execute(
                f"""DELETE FROM {SCHEMA}.EMBEDDING_METADATA
                WHERE CHUNK_ID IN (
                    SELECT CHUNK_ID FROM {SCHEMA}.DOCUMENT_CHUNKS
                    WHERE DOC_ID = %s AND VERSION = %s
                )""",
                (document.doc_id, document.version),
            )
            cursor.execute(
                f"DELETE FROM {SCHEMA}.DOCUMENT_CHUNKS WHERE DOC_ID = %s AND VERSION = %s",
                (document.doc_id, document.version),
            )

        chunk_sql = f"""
            INSERT INTO {SCHEMA}.DOCUMENT_CHUNKS (
                CHUNK_ID, DOC_ID, VERSION, SECTION_ID, SECTION_TITLE, CHUNK_INDEX,
                CHUNK_TEXT, TOKEN_COUNT, CONTENT_HASH, COUNTRY, BUSINESS_UNIT,
                ACCESS_LEVEL, EFFECTIVE_DATE, EXPIRY_DATE, EMBEDDING, CREATED_AT
            ) SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                PARSE_JSON(%s), %s
        """
        # Snowflake Connector's executemany rewrite supports INSERT ... VALUES,
        # but not this INSERT ... SELECT ... PARSE_JSON bind. The governed
        # corpus is intentionally small (40 sections), so deterministic
        # row-wise execution is safer than relying on an unsupported rewrite.
        for chunk in chunks:
            cursor.execute(
                chunk_sql,
                (
                    chunk.chunk_id,
                    chunk.metadata.doc_id,
                    chunk.metadata.version,
                    chunk.section_id,
                    chunk.section_title,
                    chunk.chunk_index,
                    chunk.chunk_text,
                    chunk.token_count,
                    chunk.content_hash,
                    chunk.metadata.country,
                    chunk.metadata.business_unit,
                    chunk.metadata.access_level,
                    chunk.metadata.effective_date,
                    chunk.metadata.expiry_date,
                    json.dumps(chunk.embedding),
                    now,
                ),
            )
        cursor.executemany(
            f"""
            INSERT INTO {SCHEMA}.EMBEDDING_METADATA (
                CHUNK_ID, EMBEDDING_MODEL, EMBEDDING_VERSION, EMBEDDING_DIMENSION,
                EMBEDDING_PROVIDER, DISTANCE_METRIC, CONTENT_HASH, GENERATED_AT
            ) VALUES (%s, %s, '1', %s, 'LOCAL_DETERMINISTIC', 'COSINE', %s, %s)
            """,
            [
                (
                    chunk.chunk_id,
                    EMBEDDING_MODEL,
                    EMBEDDING_DIMENSION,
                    chunk.content_hash,
                    now,
                )
                for chunk in chunks
            ],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
    return len(documents), len(chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("sop"))
    args = parser.parse_args()
    config = SnowflakeConfig.from_environment()
    config.validate()
    connection = connect(config)
    try:
        document_count, chunk_count = load(connection, args.corpus)
    finally:
        connection.close()
    print(f"phase5_documents_loaded={document_count}")
    print(f"phase5_chunks_loaded={chunk_count}")
    print("phase5_sop_ingestion=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

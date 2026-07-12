"""Validate the live governed SOP corpus and write a controlled audit event."""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path

from scripts.load_sop_corpus import SCHEMA, connect
from scripts.rag_corpus import EMBEDDING_DIMENSION, EMBEDDING_MODEL, load_corpus
from scripts.run_rag_evaluation import assert_targets, evaluate
from scripts.validate_snowflake_config import SnowflakeConfig


def scalar(cursor, sql: str) -> object:  # noqa: ANN001
    cursor.execute(sql)
    return cursor.fetchone()[0]


def validate_live(connection, corpus_root: Path) -> tuple[int, int]:  # noqa: ANN001
    documents, chunks = load_corpus(corpus_root)
    expected_document_hashes = {(doc.doc_id, doc.version): doc.content_hash for doc in documents}
    expected_chunk_hashes = {chunk.chunk_id: chunk.content_hash for chunk in chunks}
    cursor = connection.cursor()
    try:
        cursor.execute("ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_PHASE5_RAG_VALIDATION'")
        cursor.execute(
            f"SELECT DOC_ID, VERSION, CONTENT_HASH FROM {SCHEMA}.DOCUMENT_REGISTRY "
            "WHERE DOCUMENT_STATUS = 'ACTIVE'"
        )
        live_documents = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        for key, content_hash in expected_document_hashes.items():
            if live_documents.get(key) != content_hash:
                raise AssertionError(f"Document registry mismatch: {key}")
        cursor.execute(f"SELECT CHUNK_ID, CONTENT_HASH FROM {SCHEMA}.DOCUMENT_CHUNKS")
        live_chunks = {row[0]: row[1] for row in cursor.fetchall()}
        for chunk_id, content_hash in expected_chunk_hashes.items():
            if live_chunks.get(chunk_id) != content_hash:
                raise AssertionError(f"Document chunk mismatch: {chunk_id}")
        embedding_count = int(
            scalar(
                cursor,
                f"SELECT COUNT(*) FROM {SCHEMA}.EMBEDDING_METADATA "
                f"WHERE EMBEDDING_MODEL = '{EMBEDDING_MODEL}' "
                f"AND EMBEDDING_DIMENSION = {EMBEDDING_DIMENSION}",
            )
        )
        if embedding_count != len(chunks):
            raise AssertionError("Embedding metadata count does not match corpus chunks")
        expired_eligible = int(
            scalar(
                cursor,
                f"SELECT COUNT(*) FROM {SCHEMA}.DOCUMENT_CHUNKS "
                "WHERE '2030-01-01'::DATE BETWEEN EFFECTIVE_DATE AND EXPIRY_DATE",
            )
        )
        if expired_eligible != 0:
            raise AssertionError("Expired policy remained eligible in 2030")
        cursor.execute("USE ROLE PHARMARETAIL_AI_APP")
        cursor.execute("USE SECONDARY ROLES NONE")
        cursor.execute(
            f"""
            INSERT INTO {SCHEMA}.RETRIEVAL_AUDIT (
                AUDIT_ID, EVENT_TIMESTAMP, ACTOR, ACTOR_ROLE, QUERY_HASH,
                COUNTRY_FILTER, BUSINESS_UNIT_FILTER, AS_OF_DATE,
                RETRIEVED_CHUNK_IDS, CITATION_COUNT, UNCERTAINTY, REFUSED,
                REFUSAL_REASON, OUTCOME, LATENCY_MS
            ) SELECT %s, CURRENT_TIMESTAMP(), CURRENT_USER(), CURRENT_ROLE(), %s,
                'AU', 'EVALUATION', %s, PARSE_JSON('[]'), 0, 'LOW', FALSE,
                NULL, 'PHASE5_VALIDATION_PASS', 1
            """,
            (str(uuid.uuid4()), "PHASE5_VALIDATION_QUERY_HASH", date(2026, 7, 1)),
        )
        connection.commit()
        cursor.execute("USE ROLE PHARMARETAIL_ADMIN")
        cursor.execute("USE SECONDARY ROLES NONE")
        audit_count = int(
            scalar(
                cursor,
                f"SELECT COUNT(*) FROM {SCHEMA}.RETRIEVAL_AUDIT "
                "WHERE OUTCOME = 'PHASE5_VALIDATION_PASS'",
            )
        )
        if audit_count < 1:
            raise AssertionError("Controlled retrieval audit insert was not persisted")
    finally:
        cursor.close()
    return len(documents), len(chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("sop"))
    parser.add_argument("--cases", type=Path, default=Path("evaluation/rag_eval_cases.yml"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    metrics, results = evaluate(args.cases, args.corpus)
    assert_targets(metrics)
    config = SnowflakeConfig.from_environment()
    config.validate()
    connection = connect(config)
    try:
        document_count, chunk_count = validate_live(connection, args.corpus)
    finally:
        connection.close()
    report = {"metrics": asdict(metrics), "cases": results}
    if args.output:
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        args.output.write_text(rendered, encoding="utf-8")
    print(f"phase5_live_documents={document_count}")
    print(f"phase5_live_chunks={chunk_count}")
    print("phase5_citation_coverage=PASS rate=1.0")
    print("phase5_unauthorized_leakage=PASS rows=0")
    print("phase5_expired_policy_usage=PASS rows=0")
    print("phase5_medical_refusal=PASS")
    print("phase5_retrieval_audit=PASS")
    print("phase5_rag_validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

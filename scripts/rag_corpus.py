"""Load and deterministically section-chunk the governed SOP corpus."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

REQUIRED_METADATA = {
    "doc_id",
    "title",
    "version",
    "effective_date",
    "expiry_date",
    "country",
    "business_unit",
    "policy_owner",
    "access_level",
    "section_id",
    "source_type",
}
ACCESS_LEVELS = {"PUBLIC", "INTERNAL", "RESTRICTED"}
SECTION_PATTERN = re.compile(r"^## \[([A-Z0-9-]+)]\s+(.+)$", re.MULTILINE)
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
EMBEDDING_DIMENSION = 64
EMBEDDING_MODEL = "DETERMINISTIC_HASHED_LEXICAL_V1"


@dataclass(frozen=True)
class DocumentMetadata:
    doc_id: str
    title: str
    version: str
    effective_date: date
    expiry_date: date
    country: str
    business_unit: str
    policy_owner: str
    access_level: str
    section_id: str
    source_type: str
    source_file: str
    content_hash: str


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    metadata: DocumentMetadata
    section_id: str
    section_title: str
    chunk_text: str
    token_count: int
    chunk_index: int
    content_hash: str
    embedding: tuple[float, ...]

    @property
    def citation(self) -> str:
        meta = self.metadata
        return (
            f"{meta.title} v{meta.version}, Section {self.section_id}, "
            f"effective {meta.effective_date.isoformat()}"
        )


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def hashed_embedding(text: str, dimension: int = EMBEDDING_DIMENSION) -> tuple[float, ...]:
    """Create a deterministic dependency-free signed feature-hashing vector."""
    vector = [0.0] * dimension
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [round(value / norm, 8) for value in vector]
    return tuple(vector)


def _parse_date(value: object, field: str, path: Path) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{path}: invalid {field}") from exc


def _parse_document(path: Path, corpus_root: Path) -> tuple[DocumentMetadata, str]:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n") or "\n---\n" not in raw[4:]:
        raise ValueError(f"{path}: missing YAML front matter")
    front_matter, body = raw[4:].split("\n---\n", 1)
    payload = yaml.safe_load(front_matter)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: front matter must be a mapping")
    missing = sorted(REQUIRED_METADATA - payload.keys())
    if missing:
        raise ValueError(f"{path}: missing metadata: {', '.join(missing)}")
    access_level = str(payload["access_level"]).upper()
    if access_level not in ACCESS_LEVELS:
        raise ValueError(f"{path}: unsupported access_level {access_level}")
    effective_date = _parse_date(payload["effective_date"], "effective_date", path)
    expiry_date = _parse_date(payload["expiry_date"], "expiry_date", path)
    if effective_date > expiry_date:
        raise ValueError(f"{path}: effective_date is after expiry_date")
    relative_path = path.relative_to(corpus_root.parent).as_posix()
    metadata = DocumentMetadata(
        doc_id=str(payload["doc_id"]),
        title=str(payload["title"]),
        version=str(payload["version"]),
        effective_date=effective_date,
        expiry_date=expiry_date,
        country=str(payload["country"]).upper(),
        business_unit=str(payload["business_unit"]).upper(),
        policy_owner=str(payload["policy_owner"]),
        access_level=access_level,
        section_id=str(payload["section_id"]),
        source_type=str(payload["source_type"]).upper(),
        source_file=relative_path,
        content_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )
    return metadata, body.strip()


def _section_chunks(metadata: DocumentMetadata, body: str) -> list[DocumentChunk]:
    matches = list(SECTION_PATTERN.finditer(body))
    if not matches:
        raise ValueError(f"{metadata.source_file}: no section headings found")
    chunks: list[DocumentChunk] = []
    seen_sections: set[str] = set()
    for index, match in enumerate(matches):
        section_id, section_title = match.group(1), match.group(2).strip()
        if section_id in seen_sections:
            raise ValueError(f"{metadata.source_file}: duplicate section {section_id}")
        seen_sections.add(section_id)
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        text = re.sub(r"\s+", " ", body[content_start:content_end]).strip()
        if not text:
            raise ValueError(f"{metadata.source_file}: empty section {section_id}")
        chunk_material = f"{metadata.doc_id}|{metadata.version}|{section_id}|{text}"
        content_hash = hashlib.sha256(chunk_material.encode("utf-8")).hexdigest()
        chunks.append(
            DocumentChunk(
                chunk_id=f"CHK-{content_hash[:24].upper()}",
                metadata=metadata,
                section_id=section_id,
                section_title=section_title,
                chunk_text=text,
                token_count=len(tokenize(text)),
                chunk_index=index + 1,
                content_hash=content_hash,
                embedding=hashed_embedding(f"{metadata.title} {section_title} {text}"),
            )
        )
    return chunks


def load_corpus(
    corpus_root: Path = Path("sop"),
) -> tuple[list[DocumentMetadata], list[DocumentChunk]]:
    documents: list[DocumentMetadata] = []
    chunks: list[DocumentChunk] = []
    seen_versions: set[tuple[str, str]] = set()
    for path in sorted(corpus_root.glob("*.md")):
        metadata, body = _parse_document(path, corpus_root)
        key = (metadata.doc_id, metadata.version)
        if key in seen_versions:
            raise ValueError(f"Duplicate document version: {metadata.doc_id} v{metadata.version}")
        seen_versions.add(key)
        documents.append(metadata)
        chunks.extend(_section_chunks(metadata, body))
    if not 6 <= len(documents) <= 8:
        raise ValueError(f"Expected 6-8 governed documents, found {len(documents)}")
    return documents, chunks

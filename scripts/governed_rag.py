"""Deterministic governed SOP retrieval with citations and refusal guardrails."""

from __future__ import annotations

import hashlib
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from scripts.rag_corpus import DocumentChunk, load_corpus, tokenize

ROLE_ACCESS = {
    "PHARMARETAIL_ADMIN": {"PUBLIC", "INTERNAL", "RESTRICTED"},
    "PHARMARETAIL_AI_APP": {"PUBLIC", "INTERNAL", "RESTRICTED"},
    "PHARMARETAIL_SUPPLY_CHAIN_ANALYST": {"PUBLIC", "INTERNAL", "RESTRICTED"},
    "PHARMARETAIL_AREA_MANAGER": {"PUBLIC", "INTERNAL"},
    "PHARMARETAIL_STORE_MANAGER": {"PUBLIC", "INTERNAL"},
    "PHARMARETAIL_READONLY": {"PUBLIC"},
}
PROMPT_INJECTION_PATTERNS = (
    r"ignore (?:all |the )?(?:previous|prior|system) instructions",
    r"reveal (?:the )?(?:system|developer) prompt",
    r"bypass (?:the )?(?:access|role|security|citation)",
    r"disable (?:the )?(?:guardrail|filter|citation)",
    r"pretend (?:you are|to be) (?:an )?admin",
    r"execute (?:this )?(?:code|sql|command)",
    r"show (?:me )?(?:restricted|hidden|secret) documents",
)
MEDICAL_PATTERNS = (
    r"\bdiagnos(?:e|is|ing)\b",
    r"\bdos(?:e|age|ing)\b",
    r"\bwhat medicine\b",
    r"\bcan i take\b",
    r"\bsafe (?:for|to use|to take)\b",
    r"\btreat(?:ment| my| this)\b",
    r"\bsymptoms?\b",
    r"\bcontraindicat",
    r"\bpregnan",
    r"\bsubstitut(?:e|ion)\b.*\bmedicine\b",
    r"\bmedicine\b.*\bsubstitut(?:e|ion)\b",
    r"\boverdose\b",
)


@dataclass(frozen=True)
class RetrievalFilters:
    country: str = "AU"
    business_units: tuple[str, ...] = ()
    doc_ids: tuple[str, ...] = ()
    as_of_date: date = date(2026, 7, 1)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    answer: str
    citations: tuple[str, ...]
    retrieved: tuple[RetrievedChunk, ...]
    uncertainty: str
    uncertainty_score: float
    refused: bool
    refusal_reason: str | None
    latency_ms: int
    query_hash: str
    filters_applied: dict[str, object] = field(default_factory=dict)


class GovernedRetriever:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        document_frequency: Counter[str] = Counter()
        for chunk in chunks:
            document_frequency.update(set(tokenize(self._search_text(chunk))))
        total = max(len(chunks), 1)
        self.idf = {
            token: math.log((total + 1) / (frequency + 1)) + 1
            for token, frequency in document_frequency.items()
        }

    @classmethod
    def from_corpus(cls, corpus_root: Path = Path("sop")) -> "GovernedRetriever":
        _, chunks = load_corpus(corpus_root)
        return cls(chunks)

    @staticmethod
    def _search_text(chunk: DocumentChunk) -> str:
        return f"{chunk.metadata.title} {chunk.section_title} {chunk.chunk_text}"

    @staticmethod
    def _matches_any(patterns: tuple[str, ...], query: str) -> bool:
        return any(re.search(pattern, query, flags=re.IGNORECASE) for pattern in patterns)

    def _eligible(self, chunk: DocumentChunk, role: str, filters: RetrievalFilters) -> bool:
        allowed = ROLE_ACCESS.get(role.upper(), set())
        metadata = chunk.metadata
        return (
            metadata.access_level in allowed
            and metadata.country == filters.country.upper()
            and metadata.effective_date <= filters.as_of_date <= metadata.expiry_date
            and (not filters.business_units or metadata.business_unit in filters.business_units)
            and (not filters.doc_ids or metadata.doc_id in filters.doc_ids)
        )

    def _score(self, query: str, chunk: DocumentChunk) -> float:
        query_counts = Counter(tokenize(query))
        if not query_counts:
            return 0.0
        body_counts = Counter(tokenize(self._search_text(chunk)))
        numerator = sum(
            min(count, body_counts[token]) * self.idf.get(token, 1.0)
            for token, count in query_counts.items()
            if token in body_counts
        )
        denominator = sum(count * self.idf.get(token, 1.0) for token, count in query_counts.items())
        title_tokens = set(tokenize(chunk.metadata.title))
        title_overlap = len(set(query_counts) & title_tokens) / max(len(set(query_counts)), 1)
        return round(min(1.0, numerator / max(denominator, 1.0) + 0.25 * title_overlap), 6)

    def _retrieve(
        self, query: str, role: str, filters: RetrievalFilters, top_k: int
    ) -> tuple[RetrievedChunk, ...]:
        ranked = [
            RetrievedChunk(chunk=chunk, score=self._score(query, chunk))
            for chunk in self.chunks
            if self._eligible(chunk, role, filters)
        ]
        ranked = [item for item in ranked if item.score >= 0.12]
        ranked.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        return tuple(ranked[:top_k])

    @staticmethod
    def _query_hash(query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()

    def answer(
        self,
        query: str,
        role: str,
        filters: RetrievalFilters | None = None,
        *,
        top_k: int = 3,
    ) -> RetrievalResult:
        started = time.perf_counter()
        filters = filters or RetrievalFilters()
        query_hash = self._query_hash(query)
        applied = {
            "country": filters.country,
            "business_units": list(filters.business_units),
            "doc_ids": list(filters.doc_ids),
            "as_of_date": filters.as_of_date.isoformat(),
            "role": role.upper(),
        }

        def result(
            answer: str,
            *,
            retrieved: tuple[RetrievedChunk, ...] = (),
            refused: bool,
            reason: str | None,
            uncertainty: str,
            uncertainty_score: float,
        ) -> RetrievalResult:
            citations = tuple(dict.fromkeys(item.chunk.citation for item in retrieved))
            return RetrievalResult(
                answer=answer,
                citations=citations,
                retrieved=retrieved,
                uncertainty=uncertainty,
                uncertainty_score=uncertainty_score,
                refused=refused,
                refusal_reason=reason,
                latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
                query_hash=query_hash,
                filters_applied=applied,
            )

        if self._matches_any(PROMPT_INJECTION_PATTERNS, query):
            return result(
                "Request refused because it attempts to override retrieval security controls.",
                refused=True,
                reason="PROMPT_INJECTION",
                uncertainty="HIGH",
                uncertainty_score=1.0,
            )
        if self._matches_any(MEDICAL_PATTERNS, query):
            medical_filters = RetrievalFilters(
                country=filters.country,
                business_units=(),
                doc_ids=("POL-MEDICAL-ADVICE-BOUNDARY",),
                as_of_date=filters.as_of_date,
            )
            medical = self._retrieve(
                "medical advice diagnosis dosage treatment patient safety refusal",
                role,
                medical_filters,
                1,
            )
            if medical:
                return result(
                    "Medical advice cannot be provided. Contact a pharmacist, doctor, emergency "
                    "service, or other qualified professional as appropriate.",
                    retrieved=medical,
                    refused=True,
                    reason="MEDICAL_ADVICE_BOUNDARY",
                    uncertainty="LOW",
                    uncertainty_score=0.05,
                )
            return result(
                "Medical advice cannot be provided, and no effective authorised boundary policy "
                "was available.",
                refused=True,
                reason="NO_AUTHORISED_SOURCE",
                uncertainty="HIGH",
                uncertainty_score=1.0,
            )

        retrieved = self._retrieve(query, role, filters, top_k)
        if not retrieved:
            return result(
                "No effective authorised source was found; the request cannot be answered.",
                refused=True,
                reason="NO_AUTHORISED_SOURCE",
                uncertainty="HIGH",
                uncertainty_score=1.0,
            )
        best_score = retrieved[0].score
        uncertainty_score = round(max(0.0, 1.0 - best_score), 4)
        uncertainty = "LOW" if best_score >= 0.65 else "MEDIUM" if best_score >= 0.35 else "HIGH"
        extracts = " ".join(item.chunk.chunk_text for item in retrieved[:2])
        answer = f"{extracts} Sources: " + "; ".join(
            f"[{index}] {item.chunk.citation}" for index, item in enumerate(retrieved, 1)
        )
        return result(
            answer,
            retrieved=retrieved,
            refused=False,
            reason=None,
            uncertainty=uncertainty,
            uncertainty_score=uncertainty_score,
        )

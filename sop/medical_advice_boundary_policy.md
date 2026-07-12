---
doc_id: POL-MEDICAL-ADVICE-BOUNDARY
title: Medical Advice Boundary Policy
version: 1.0
effective_date: 2026-01-01
expiry_date: 2027-12-31
country: AU
business_unit: ENTERPRISE
policy_owner: Chief Medical Officer
access_level: PUBLIC
section_id: DOCUMENT
source_type: SYNTHETIC_INTERNAL_POLICY
---

## [MB-01] Boundary

The operations RAG service is not a clinical decision-support system and must not diagnose, recommend treatment, select a medicine, assess individual suitability, provide dosing, or determine whether a product is safe for a person.

## [MB-02] Required refusal

Refuse questions requesting diagnosis, dosage, treatment, contraindication assessment, medicine substitution, patient-specific safety, or interpretation of symptoms. State that a pharmacist, doctor, emergency service, or other qualified professional should be contacted as appropriate.

## [MB-03] Allowed operational information

The service may explain non-clinical operational steps such as quarantine, stop-sale, recall reconciliation, incident escalation, documentation, stock movement, and approved notification routes, provided the answer remains sourced and does not infer clinical risk.

## [MB-04] Urgent situations

If a query describes immediate danger, severe symptoms, overdose, or a medical emergency, do not analyse the condition. Advise contacting local emergency services or an appropriate qualified health professional immediately.

## [MB-05] Audit requirement

Record medical-boundary refusals with a non-sensitive query hash, refusal category, policy citation, role, timestamp, and outcome. Do not retain patient names, prescription details, or health information in retrieval audit logs.

# Governed SOP corpus

The corpus contains eight synthetic internal documents written for this project.
No public dataset, copied corporate policy, patient record or external document
is used.

| Document | Version | Access | Business unit | Sections |
|---|---:|---|---|---:|
| Stock Replenishment SOP | 1.2 | INTERNAL | RETAIL_OPERATIONS | 5 |
| Supplier Escalation SOP | 2.0 | RESTRICTED | SUPPLY_CHAIN | 5 |
| Product Recall SOP | 1.4 | INTERNAL | QUALITY_AND_COMPLIANCE | 5 |
| Cold-Chain Incident SOP | 1.3 | INTERNAL | PHARMACY_OPERATIONS | 5 |
| Returns and Damaged Stock SOP | 1.1 | INTERNAL | RETAIL_OPERATIONS | 5 |
| Inventory Adjustment SOP | 1.5 | INTERNAL | RETAIL_OPERATIONS | 5 |
| AI Acceptable Use Policy | 1.0 | INTERNAL | ENTERPRISE | 5 |
| Medical Advice Boundary Policy | 1.0 | PUBLIC | ENTERPRISE | 5 |

Total: **8 documents and 40 deterministic section chunks**.

## Required metadata

Every source includes `doc_id`, `title`, `version`, `effective_date`,
`expiry_date`, `country`, `business_unit`, `policy_owner`, `access_level`,
`section_id` and `source_type`. The parser fails closed on missing fields,
unsupported access levels, invalid dates, duplicate versions, duplicate section
IDs, empty sections, or any count other than exactly 8 documents and 40 chunks.

`section_id: DOCUMENT` identifies the document-level registry record. Each chunk
replaces it with its explicit section heading ID, such as `SR-02` or `CC-04`.

## Version and lifecycle behavior

Registry identity is `(doc_id, version)`. Re-ingesting the same version updates
its hash and replaces only that version's chunks and embedding metadata. Other
versions remain governed records. Retrieval requires:

```text
effective_date <= requested_as_of_date <= expiry_date
```

Expired or not-yet-effective documents never participate in ranking.

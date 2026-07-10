# Data Readiness

## Scope

This assessment covers only the downloaded UCI, OpenStreetMap (OSM), and Open Food Facts files plus the two seed dimensions created from them. No datasets were joined and no new source data was downloaded.

## Source and target classification

| Dataset | Classification | Current use | Intended future table |
|---|---|---|---|
| `data/uci/online_retail_II.xlsx` | Real, public transactional data | Profiled only; not transformed or joined | Raw sales input, then a future sales fact after source-specific cleaning |
| `data/uci/online_retail_ii.zip` | Real, public source archive | Preserved as the original compressed delivery | Raw/archive layer only |
| `data/osm/chemist_warehouse_stores.json` | Real, public OSM data | Source for the 100-row store seed | `dim_store` |
| `data/openfoodfacts/vitamins.json` | Real, public product sample | Product-name and brand examples only | Reference input for future product-catalog curation; not a fact table |
| `data/openfoodfacts/baby-foods.json` | Real, public product sample | Product-name and brand examples only | Reference input for future product-catalog curation; not a fact table |
| `data/openfoodfacts/oral-care.json` | Real API response with zero products | Excluded from use | None |
| `data/openfoodfacts/skin-care.json` | Real API response with zero products | Excluded from use | None |
| `data/processed/dim_store_seed.csv` | Derived from real OSM records | Clean 100-store seed with stable OSM-based IDs | `dim_store` seed |
| `data/processed/dim_product_seed.csv` | Fully synthetic, controlled catalog | 300-row pharmacy-retail product seed | `dim_product` seed |

## Seed construction

### Store seed

- Selected 100 OSM records deterministically, prioritising populated postcode, state, location label, and street fields.
- `store_id` preserves OSM lineage using element type and OSM ID.
- Latitude and longitude are taken directly from the OSM element or its returned centre point.
- State is taken from `addr:state`, then derived from an available Australian postcode. Where both were absent, state was assigned from the nearest state-known OSM store in the same downloaded dataset.
- Region mapping is controlled: NSW/ACT → `NSW & ACT`, VIC/TAS → `VIC & TAS`, QLD → `QLD`, SA/NT → `SA & NT`, WA → `WA`.
- Missing postcodes were left blank rather than fabricated.

### Product seed

- All 300 products are synthetic; Open Food Facts rows were not copied into the seed catalog.
- The catalog uses seven controlled categories: `vitamins`, `skincare`, `oral care`, `baby care`, `pain relief`, `cold & flu`, and `personal care`.
- Product IDs are unique and deterministic (`PRD0001`–`PRD0300`).
- Cold-chain and regulated-product flags are scenario rules for demonstration data. They are not validated clinical, legal, or Therapeutic Goods Administration classifications.

## UCI Online Retail II profile

The workbook was inspected as invoice-line data across both sheets and was not joined to the store or product seeds.

| Check | Result |
|---|---:|
| Sheets | 2 (`Year 2009-2010`, `Year 2010-2011`) |
| Rows | 1,067,371 |
| Columns | 8 |
| Date range | 2009-12-01 07:45 to 2011-12-09 12:50 |
| Distinct `StockCode` values | 5,305 |
| Sales records | 1,044,420 |
| Return/cancellation records | 22,951 |
| Exact duplicate rows | 34,335 (3.22%) |
| Null `Customer ID` | 243,007 (22.77%) |
| Null `Description` | 4,382 (0.41%) |
| Zero-price rows | 6,202 (0.58%) |
| Negative-price rows | 5 |
| Zero-quantity rows | 0 |

Sales records are defined as positive quantity with an invoice not beginning with `C`. Return/cancellation records are defined as negative quantity or an invoice beginning with `C`.

## Data-quality findings

| Severity | Finding | Evidence and impact |
|---|---|---|
| High | UCI customer coverage is incomplete | 243,007 rows (22.77%) have no `Customer ID`; customer-level analysis would be biased without an explicit anonymous-customer policy. |
| High | OSM address completeness is weak | Of 421 downloaded stores, only 51 have both state and postcode. The selected seed still has 30 blank postcodes; postcode-level analysis and validation are not ready. |
| Medium | UCI contains exact duplicate invoice lines | 34,335 rows (3.22%) are exact duplicates. A future sales fact needs a documented deduplication rule before aggregation. |
| Medium | UCI contains non-standard price records | 6,202 zero-price and 5 negative-price rows can distort revenue and margin metrics unless classified or excluded by an approved rule. |
| Medium | Open Food Facts baby-food sample is partial | API reports 137 matching products, but only the first 100 were downloaded. Two downloaded rows lack product name and two lack brand. It is suitable only as a naming/brand example. |
| Medium | Store state is partly derived | Missing OSM states were inferred only from existing downloaded postcode/state anchors. This supports a demo seed but requires authoritative address validation before production use. |
| Medium | Synthetic regulatory flags are illustrative | The product flags have not been validated against an authoritative regulatory source and must not drive compliance or clinical decisions. |
| Low | Two Open Food Facts categories are empty | `oral-care` and `skin-care` each contain zero products and are intentionally excluded. |

## Readiness decision

The two processed files are suitable as development seeds for dimensional modelling. They are not authoritative production master data. Before building downstream facts, validate store addresses/postcodes, approve product classification rules, and define UCI deduplication, return, anonymous-customer, and price-handling policies.

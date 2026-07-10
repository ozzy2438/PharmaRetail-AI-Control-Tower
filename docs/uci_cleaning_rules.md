# UCI Online Retail II cleaning rules

## Input and grain

`data/uci/online_retail_II.xlsx` contains the sheets `Year 2009-2010` and `Year 2010-2011`. They are combined at invoice-line grain. Source columns are renamed to `invoice`, `stock_code`, `description`, `quantity`, `invoice_date`, `price`, `customer_id`, and `country`.

## Type rules

- `invoice`, `stock_code`, `description`, `customer_id`, and `country` are strings.
- `quantity` is an integer and `price` is a decimal-compatible floating-point value.
- `invoice_date` is a timestamp without a separately supplied timezone; no timezone conversion is applied.
- `is_customer_identified` is a boolean derived from non-null `customer_id`.

## Classification and output rules

1. Combine the two sheets, then remove exact duplicates across the eight source fields.
2. Send any deduplicated row with `price <= 0` to `data/quarantine/uci_invalid_price.parquet` with `quarantine_reason = non_positive_price`.
3. From the remaining valid-price rows, classify a record as a return when `quantity < 0` or `invoice` begins with `C`. Write returns to `data/processed/uci_returns_clean.parquet`.
4. Write the remaining positive-quantity, valid-price, non-cancellation records to `data/processed/uci_sales_clean.parquet`.
5. Retain sales rows with null `customer_id`; set `is_customer_identified = false`. They must be excluded from future customer-level analysis rather than removed from sales reporting.

Quarantine has precedence over return classification. Therefore, a cancellation/negative-quantity row with non-positive price appears only in the quarantine file, preventing the same source row from being counted in two outputs.

## Run results

| Metric | Result |
|---|---:|
| Combined source rows | 1,067,371 |
| Exact duplicates removed | 34,335 |
| Deduplicated rows | 1,033,036 |
| Sales output | 1,007,913 |
| Returns output | 19,104 |
| Invalid-price quarantine | 6,019 |
| Invalid-price rows that also matched return logic | 3,393 |
| Sales rows with null `customer_id` | 228,488 |

The sales staging output has no null invoice dates, no non-positive quantities, and no non-positive prices.

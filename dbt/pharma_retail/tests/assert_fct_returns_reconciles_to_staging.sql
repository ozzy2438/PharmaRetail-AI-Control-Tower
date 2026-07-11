-- Return-value reconciliation, mirroring assert_fct_sales_daily_reconciles_to_staging.sql
-- (see that file for why the tolerance isn't tighter, and why the coalesce
-- to 0 is needed: an empty table's SUM is NULL, which would otherwise make
-- the comparison NULL and silently pass instead of failing).
with staging_total as (
    select coalesce(sum(line_return_value), 0) as total from {{ ref('stg_uci_returns') }}
),

mart_total as (
    select coalesce(sum(total_return_value), 0) as total from {{ ref('fct_returns') }}
)

select
    staging_total.total as staging_total_return_value,
    mart_total.total as mart_total_return_value
from staging_total, mart_total
where abs(staging_total.total - mart_total.total) > 1.00

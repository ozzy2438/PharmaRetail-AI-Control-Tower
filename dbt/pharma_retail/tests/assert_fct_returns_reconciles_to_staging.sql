-- Return-value reconciliation, mirroring assert_fct_sales_daily_reconciles_to_staging.sql.
with staging_total as (
    select sum(line_return_value) as total from {{ ref('stg_uci_returns') }}
),

mart_total as (
    select sum(total_return_value) as total from {{ ref('fct_returns') }}
)

select
    staging_total.total as staging_total_return_value,
    mart_total.total as mart_total_return_value
from staging_total, mart_total
where abs(staging_total.total - mart_total.total) > 0.01

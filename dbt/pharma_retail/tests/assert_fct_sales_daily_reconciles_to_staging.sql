-- Revenue reconciliation: total revenue in the mart must equal total
-- revenue in staging, so the daily/country aggregation (int_sales_daily)
-- and the dim_date inner join (fct_sales_daily) neither dropped nor
-- double-counted any line. A 1-cent tolerance absorbs floating-point noise.
with staging_total as (
    select sum(line_revenue) as total from {{ ref('stg_uci_sales') }}
),

mart_total as (
    select sum(total_revenue) as total from {{ ref('fct_sales_daily') }}
)

select
    staging_total.total as staging_total_revenue,
    mart_total.total as mart_total_revenue
from staging_total, mart_total
where abs(staging_total.total - mart_total.total) > 0.01

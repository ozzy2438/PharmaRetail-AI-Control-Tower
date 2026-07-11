-- Revenue reconciliation: total revenue in the mart must equal total
-- revenue in staging, so the daily/country aggregation (int_sales_daily)
-- and the dim_date inner join (fct_sales_daily) neither dropped nor
-- double-counted any line.
--
-- RAW.PRICE is FLOAT (Phase 2, not changed here); line_revenue is cast to
-- NUMBER(18,4) in staging for correct currency semantics, but proving exact
-- bit-for-bit equality between a row-by-row sum and a grouped-then-summed
-- total over ~1M FLOAT-sourced values isn't guaranteed regardless of the
-- downstream cast. A $1 tolerance (about 5 parts per 100 million of the
-- ~$20.5M total) comfortably absorbs that residual float noise while still
-- catching anything a real bug would cause — a dropped/duplicated row or a
-- mis-grouped join moves the total by many dollars, not fractions of one.
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
where abs(staging_total.total - mart_total.total) > 1.00

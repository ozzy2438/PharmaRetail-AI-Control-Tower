with model_totals as (
    select
        coalesce(sum(units_sold), 0) as units_sold,
        coalesce(sum(gross_sales), 0) as gross_sales
    from {{ ref('int_sales_daily') }}
),

staging_totals as (
    select
        coalesce(sum(quantity), 0) as units_sold,
        coalesce(sum(line_revenue), 0) as gross_sales
    from {{ ref('stg_uci_sales') }}
)

select *
from model_totals
cross join staging_totals
where model_totals.units_sold != staging_totals.units_sold
    or abs(model_totals.gross_sales - staging_totals.gross_sales) > 0.01

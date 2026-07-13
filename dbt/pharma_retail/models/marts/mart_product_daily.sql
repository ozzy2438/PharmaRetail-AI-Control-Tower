-- Daily product rollup. The return rate is quantity-weighted across stores.
with store_product_daily as (
    select
        product_id,
        date,
        store_id,
        units_sold,
        returned_units,
        gross_sales
    from {{ ref('int_store_product_daily') }}
)

select
    product_id,
    date,
    sum(units_sold) as total_units,
    sum(gross_sales) as total_sales,
    coalesce(sum(returned_units) / nullif(sum(units_sold), 0), 0.0) as return_rate,
    count(distinct iff(units_sold > 0, store_id, null)) as active_store_count
from store_product_daily
group by product_id, date

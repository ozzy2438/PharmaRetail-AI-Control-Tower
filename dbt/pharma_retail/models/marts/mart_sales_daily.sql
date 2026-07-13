-- Governed sales mart at the store-product-date grain.  The intermediate
-- model already preserves sales-only, return-only and mixed activity days.
with store_product_daily as (
    select
        store_id,
        product_id,
        date,
        units_sold,
        gross_sales,
        net_sales,
        return_rate
    from {{ ref('int_store_product_daily') }}
)

select
    store_id,
    product_id,
    date,
    units_sold,
    gross_sales,
    net_sales,
    return_rate,
    coalesce(gross_sales / nullif(units_sold, 0), 0.0) as average_unit_price
from store_product_daily

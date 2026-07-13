-- Daily store rollup. total_sales is gross sales and total_returns is the
-- positive return value, so downstream users can derive net sales explicitly.
with store_product_daily as (
    select
        store_id,
        date,
        product_id,
        units_sold,
        gross_sales,
        return_value,
        transaction_count
    from {{ ref('int_store_product_daily') }}
)

select
    store_id,
    date,
    sum(gross_sales) as total_sales,
    sum(return_value) as total_returns,
    sum(transaction_count) as transaction_count,
    count(distinct iff(units_sold > 0, product_id, null)) as active_products
from store_product_daily
group by store_id, date

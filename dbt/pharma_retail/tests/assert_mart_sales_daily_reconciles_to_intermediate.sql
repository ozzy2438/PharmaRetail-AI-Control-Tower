with expected as (
    select
        store_id,
        product_id,
        date,
        units_sold,
        gross_sales,
        net_sales,
        return_rate,
        coalesce(gross_sales / nullif(units_sold, 0), 0.0) as average_unit_price
    from {{ ref('int_store_product_daily') }}
),

actual as (
    select * from {{ ref('mart_sales_daily') }}
)

select
    coalesce(expected.store_id, actual.store_id) as store_id,
    coalesce(expected.product_id, actual.product_id) as product_id,
    coalesce(expected.date, actual.date) as date
from expected
full outer join actual
    on expected.store_id = actual.store_id
    and expected.product_id = actual.product_id
    and expected.date = actual.date
where actual.store_id is null
    or expected.store_id is null
    or expected.units_sold != actual.units_sold
    or abs(expected.gross_sales - actual.gross_sales) > 0.01
    or abs(expected.net_sales - actual.net_sales) > 0.01
    or abs(expected.return_rate - actual.return_rate) > 0.000001
    or abs(expected.average_unit_price - actual.average_unit_price) > 0.000001

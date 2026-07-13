with expected as (
    select
        product_id,
        date,
        sum(units_sold) as total_units,
        sum(gross_sales) as total_sales,
        coalesce(sum(returned_units) / nullif(sum(units_sold), 0), 0.0) as return_rate,
        count(distinct iff(units_sold > 0, store_id, null)) as active_store_count
    from {{ ref('int_store_product_daily') }}
    group by product_id, date
),

actual as (
    select * from {{ ref('mart_product_daily') }}
)

select coalesce(expected.product_id, actual.product_id) as product_id, coalesce(expected.date, actual.date) as date
from expected
full outer join actual
    on expected.product_id = actual.product_id
    and expected.date = actual.date
where actual.product_id is null
    or expected.product_id is null
    or expected.total_units != actual.total_units
    or abs(expected.total_sales - actual.total_sales) > 0.01
    or abs(expected.return_rate - actual.return_rate) > 0.000001
    or expected.active_store_count != actual.active_store_count

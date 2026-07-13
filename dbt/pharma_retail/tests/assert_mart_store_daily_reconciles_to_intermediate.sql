with expected as (
    select
        store_id,
        date,
        sum(gross_sales) as total_sales,
        sum(return_value) as total_returns,
        sum(transaction_count) as transaction_count,
        count(distinct iff(units_sold > 0, product_id, null)) as active_products
    from {{ ref('int_store_product_daily') }}
    group by store_id, date
),

actual as (
    select * from {{ ref('mart_store_daily') }}
)

select coalesce(expected.store_id, actual.store_id) as store_id, coalesce(expected.date, actual.date) as date
from expected
full outer join actual
    on expected.store_id = actual.store_id
    and expected.date = actual.date
where actual.store_id is null
    or expected.store_id is null
    or abs(expected.total_sales - actual.total_sales) > 0.01
    or abs(expected.total_returns - actual.total_returns) > 0.01
    or expected.transaction_count != actual.transaction_count
    or expected.active_products != actual.active_products

{{ config(tags=['intermediate_foundation']) }}

-- Full outer join preserves sales-only, return-only and mixed days at the
-- governed store_id + product_id + date grain.
with sales as (
    select
        store_id,
        product_id,
        date,
        units_sold,
        gross_sales,
        transaction_count
    from {{ ref('int_sales_daily') }}
),

returns as (
    select
        store_id,
        product_id,
        date,
        returned_units,
        return_value,
        return_transaction_count
    from {{ ref('int_returns_daily') }}
),

combined as (
    select
        coalesce(sales.store_id, returns.store_id) as store_id,
        coalesce(sales.product_id, returns.product_id) as product_id,
        coalesce(sales.date, returns.date) as date,
        coalesce(sales.units_sold, 0) as units_sold,
        coalesce(sales.gross_sales, 0) as gross_sales,
        coalesce(sales.transaction_count, 0) as transaction_count,
        coalesce(returns.returned_units, 0) as returned_units,
        coalesce(returns.return_value, 0) as return_value,
        coalesce(returns.return_transaction_count, 0) as return_transaction_count
    from sales
    full outer join returns
        on sales.store_id = returns.store_id
        and sales.product_id = returns.product_id
        and sales.date = returns.date
)

select
    store_id,
    product_id,
    date,
    units_sold,
    units_sold - returned_units as net_units,
    gross_sales - return_value as net_sales,
    gross_sales,
    returned_units,
    return_value,
    case
        when units_sold > 0 then returned_units / units_sold::float
        else 0.0
    end as return_rate,
    units_sold > 0 as has_sales_flag,
    returned_units > 0 as has_return_flag,
    transaction_count,
    return_transaction_count
from combined

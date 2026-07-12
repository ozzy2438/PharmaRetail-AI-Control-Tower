{{ config(tags=['intermediate_foundation']) }}

-- Use the exact same stable invoice/stock_code mapping as int_sales_daily so
-- sales and returns can be joined at store-product-date grain.
with stores as (
    select
        store_id,
        row_number() over (order by store_id) - 1 as store_index,
        count(*) over () as store_count
    from {{ ref('stg_store') }}
),

products as (
    select
        product_id,
        row_number() over (order by product_id) - 1 as product_index,
        count(*) over () as product_count
    from {{ ref('stg_product') }}
),

mapped_returns as (
    select
        stores.store_id,
        products.product_id,
        returns.*
    from {{ ref('stg_uci_returns') }} as returns
    cross join (select max(store_count) as store_count from stores) as store_counts
    cross join (select max(product_count) as product_count from products) as product_counts
    inner join stores
        on stores.store_index = mod(
            abs(hash(returns.invoice_number, returns.stock_code, 'intermediate-map-v1')),
            store_counts.store_count
        )
    inner join products
        on products.product_index = mod(
            abs(hash(returns.invoice_number, returns.stock_code, 'intermediate-map-v1')),
            product_counts.product_count
        )
),

aggregated as (
    select
        store_id,
        product_id,
        invoice_date_day as date,
        sum(abs(quantity)) as returned_units,
        sum(abs(line_return_value)) as return_value,
        count(distinct invoice_number) as return_transaction_count,
        -- Compatibility aliases retained for the existing date/country MARTS.
        invoice_date_day,
        'AU' as country,
        count(distinct invoice_number) as return_invoice_count,
        sum(abs(quantity)) as total_quantity_returned,
        sum(abs(line_return_value)) as total_return_value
    from mapped_returns
    group by store_id, product_id, invoice_date_day
)

select * from aggregated

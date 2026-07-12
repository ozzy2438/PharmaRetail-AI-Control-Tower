{{ config(tags=['intermediate_foundation']) }}

-- The UCI source has no store_id/product_id keys. This phase creates a stable
-- analytical mapping to the existing synthetic dimensions without changing
-- RAW or STAGING: the same invoice/stock_code hash always selects the same
-- dimension row, and the row-number maps are ordered by their stable IDs.
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

mapped_sales as (
    select
        stores.store_id,
        products.product_id,
        sales.*
    from {{ ref('stg_uci_sales') }} as sales
    cross join (select max(store_count) as store_count from stores) as store_counts
    cross join (select max(product_count) as product_count from products) as product_counts
    inner join stores
        on stores.store_index = mod(
            abs(hash(sales.invoice_number, sales.stock_code, 'intermediate-map-v1')),
            store_counts.store_count
        )
    inner join products
        on products.product_index = mod(
            abs(hash(sales.invoice_number, sales.stock_code, 'intermediate-map-v1')),
            product_counts.product_count
        )
),

aggregated as (
    select
        store_id,
        product_id,
        invoice_date_day as date,
        sum(quantity) as units_sold,
        sum(line_revenue) as gross_sales,
        count(distinct invoice_number) as transaction_count,
        sum(line_revenue) / nullif(sum(quantity), 0) as average_unit_price,
        count(distinct iff(
            not coalesce(is_customer_identified, false), invoice_number, null
        )) / nullif(count(distinct invoice_number), 0)::float as anonymous_customer_rate,
        -- Compatibility aliases retained for the existing date/country MARTS;
        -- this model's governed grain and foundation fields are above.
        invoice_date_day,
        'AU' as country,
        count(distinct invoice_number) as invoice_count,
        count(distinct iff(is_customer_identified, customer_id, null))
            as distinct_customer_count,
        sum(quantity) as total_quantity,
        sum(line_revenue) as total_revenue
    from mapped_sales
    group by store_id, product_id, invoice_date_day
)

select * from aggregated

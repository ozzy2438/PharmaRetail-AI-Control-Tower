{{ config(tags=['intermediate_foundation']) }}

with mapped_sales as (
    {{ map_uci_lines('stg_uci_sales', 'sales') }}
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
        min(country) as country,
        count(distinct invoice_number) as invoice_count,
        count(distinct iff(is_customer_identified, customer_id, null))
            as distinct_customer_count,
        sum(quantity) as total_quantity,
        sum(line_revenue) as total_revenue
    from mapped_sales
    group by store_id, product_id, invoice_date_day
)

select * from aggregated

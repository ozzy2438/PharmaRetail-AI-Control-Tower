-- Daily sales aggregated at (invoice_date_day, country) grain — the finest
-- grain fct_sales_daily needs, and the natural join point to dim_date.
with sales as (
    select * from {{ ref('stg_uci_sales') }}
),

aggregated as (
    select
        invoice_date_day,
        country,
        count(distinct invoice_number) as invoice_count,
        count(distinct customer_id) as distinct_customer_count,
        sum(quantity) as total_quantity,
        sum(line_revenue) as total_revenue
    from sales
    group by invoice_date_day, country
)

select * from aggregated

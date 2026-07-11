-- Sales summarised by country — the finest location grain the UCI Online
-- Retail dataset actually has (a single UK-based online retailer, no
-- physical stores). NOT joined to dim_store (contracts/dim_store.yml's
-- Australian Chemist Warehouse seed): the two datasets share no store-level
-- key. "country" stands in as the closest available geographic dimension.
-- See dbt/pharma_retail/README.md for why they aren't joined.
with sales as (
    select * from {{ ref('stg_uci_sales') }}
),

aggregated as (
    select
        country,
        count(distinct invoice_number) as invoice_count,
        count(distinct customer_id) as distinct_customer_count,
        sum(quantity) as total_quantity,
        sum(line_revenue) as total_revenue
    from sales
    group by country
)

select * from aggregated

-- Sales summarised by UCI's own product identifier (stock_code) — the UCI
-- Online Retail dataset's real product-level grain. NOT joined to
-- dim_product (contracts/dim_product.yml's synthetic PRD0001-PRD0300
-- catalog): stock_code and product_id are different, unrelated identifier
-- spaces. See dbt/pharma_retail/README.md for why they aren't joined.
with sales as (
    select * from {{ ref('stg_uci_sales') }}
),

aggregated as (
    select
        stock_code,
        any_value(product_description) as product_description,
        count(distinct invoice_number) as invoice_count,
        sum(quantity) as total_quantity,
        sum(line_revenue) as total_revenue,
        min(invoice_date_day) as first_sale_date,
        max(invoice_date_day) as last_sale_date
    from sales
    group by stock_code
)

select * from aggregated

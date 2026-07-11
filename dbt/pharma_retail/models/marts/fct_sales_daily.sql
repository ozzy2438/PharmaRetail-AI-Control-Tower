-- Daily sales fact at (date_day, country) grain, from the real UCI Online
-- Retail dataset. Joins to dim_date (a real, valid relationship); does not
-- join to dim_store/dim_product, which come from an unrelated synthetic
-- seed with no shared key (see README.md).
with sales as (
    select * from {{ ref('int_sales_daily') }}
),

dates as (
    select date_day from {{ ref('dim_date') }}
),

joined as (
    select
        dates.date_day,
        sales.country,
        sales.invoice_count,
        sales.distinct_customer_count,
        sales.total_quantity,
        sales.total_revenue
    from sales
    inner join dates
        on sales.invoice_date_day = dates.date_day
)

select * from joined

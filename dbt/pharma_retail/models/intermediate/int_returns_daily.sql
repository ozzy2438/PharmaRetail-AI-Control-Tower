-- Daily returns aggregated at (invoice_date_day, country) grain, mirroring
-- int_sales_daily so fct_returns can join dim_date the same way fct_sales_daily does.
with returns as (
    select * from {{ ref('stg_uci_returns') }}
),

aggregated as (
    select
        invoice_date_day,
        country,
        count(distinct invoice_number) as return_invoice_count,
        sum(abs(quantity)) as total_quantity_returned,
        sum(line_return_value) as total_return_value
    from returns
    group by invoice_date_day, country
)

select * from aggregated
